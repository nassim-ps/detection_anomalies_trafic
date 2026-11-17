# Spécification — détection d'anomalies sur trafic web simulé

> Projet d'apprentissage centré sur le **ML** (prévision et détection d'anomalies). MLflow, cron et Grafana sont l'outillage, pas l'objet d'étude.

## 1. Contexte

- Un simulateur génère du trafic sur une page web locale.
- La télémétrie passe par **Umami**, qui stocke ses événements dans **PostgreSQL** (tables `website_event`, `session` ; noms exacts à confirmer selon la version).
- Tout est dans le même serveur PostgreSQL : base Umami (lecture seule) + schéma **`ml`** pour tout ce que le projet produit.
- Environnement : Windows, services sous **docker-compose**.
- Les scénarios injectés (normal, pic, bot, panne, changement de comportement) sont contrôlés : ils constituent la **vérité terrain** (`ml.ground_truth`).

Diagramme de flux : [diagramme_de_flux.excalidraw](diagramme_de_flux.excalidraw).

## 2. Objectifs

### Objectifs
1. Prévoir le trafic (pages vues, visiteurs) par pas de 5 min ou 1 h.
2. Détecter les anomalies injectées et **mesurer** la détection contre `ml.ground_truth`.
3. **Comparer plusieurs méthodes sur un même protocole** (approche A) pour comprendre ce que chacune détecte ou rate.
4. Industrialiser a minima : entraînement tracé, modèle versionné, scoring horaire, dérive, ré-entraînement.

### Non-objectifs (v1)
- Classification de sessions humain/bot/conversion (LightGBM) : plus tard.
- API FastAPI, CI, tests de données avancés, Dagster : plus tard.
- DVC : pas en v1.

### Anti-objectifs (échec même si « ça marche »)
- Un modèle qui apprend les **artefacts du simulateur** plutôt que le comportement du trafic.
- Toute écriture dans les tables d'Umami.
- Des résultats non reproductibles (impossible de rejouer un run à l'identique).

## 3. Contraintes

- **Lecture seule** sur les tables Umami (rôle PostgreSQL dédié). Tout ce qui est produit va dans le schéma **`ml`**, où seul le rôle du pipeline écrit.
- Le schéma interne d'Umami change selon les versions : la lecture passe **uniquement** par des vues SQL (`sql/`).
- Umami identifie les sessions par un hash à sel tournant : travailler au niveau **session** ou **agrégat temporel**, jamais utilisateur sur plusieurs périodes (fréquence de rotation à vérifier).
- Simulateur réaliste : cycles jour/nuit, user-agents et référents variés, délais aléatoires.

## 4. Scénarios (vérité terrain)

Chaque scénario est un fichier YAML versionné dans `scenarios/` avec une graine. Chaque exécution écrit une ligne dans `ml.ground_truth (scenario, debut, fin, parametres)`.

| Scénario | Effet attendu | Paramètres |
|---|---|---|
| normal | trafic de base avec saisonnalité jour/semaine | volume moyen, amplitude jour/nuit, bruit |
| pic | hausse brutale et temporaire | facteur ×3 à ×10, durée 15 min à 2 h |
| bot | trafic répétitif, UA/référent homogènes, délais réguliers | part du trafic 10–50 %, durée |
| panne | chute proche de zéro | durée 10 min à 3 h |
| changement de comportement | nouveau régime durable (pages, horaires, volume) | date de bascule, ampleur |

Un **jeu d'évaluation fixe** (liste de scénarios + graines) est défini une fois et réutilisé pour comparer toutes les méthodes.

## 5. Modèles (approche A : comparaison)

| # | Méthode | Rôle |
|---|---|---|
| 0 | Référence naïve : écart à la même heure de la semaine précédente | plancher à battre |
| 1 | Prévision **statsforecast** (ou Prophet) + écart à la prévision | méthode principale |
| 2 | **Isolation Forest** sur features agrégées | détection multivariée |

Tous les modèles sont entraînés sur une **fenêtre temporelle fixe** ; scénarios, graine et fenêtre sont enregistrés comme paramètres du run MLflow.

## 6. Protocole d'évaluation

Précision et rappel contre `ml.ground_truth`, calculés **au niveau de l'événement** :

- **Rappel par type de scénario** : un scénario est détecté si au moins une alerte tombe dans `[debut, fin + tolérance]`.
- **Précision** : part des alertes qui tombent dans un scénario injecté.
- **Délai de détection** : temps entre `debut` et la première alerte.
- **Fausses alertes par jour** sur les périodes « normal ».

Résultat attendu : un tableau comparatif méthode × scénario, consigné dans MLflow.

## 7. MLOps

- **MLflow** : suivi des expériences + registre. Le scoring charge toujours `models:/<nom>@champion` ; un ré-entraînement produit `@challenger`, promu s'il est meilleur selon le protocole §6.
- **Reproductibilité** sans DVC : YAML de scénarios + graine dans Git, fenêtre d'entraînement fixe, le tout en paramètres MLflow. DVC pourra figer plus tard des instantanés Parquet.
- **Orchestration v1** : scripts Python + Makefile + cron, via un conteneur planificateur dans le docker-compose (image Python + `supercronic` + `crontab` versionné lançant des cibles `make`). Pas le Planificateur de tâches Windows.
- **Dérive** : rapport Evidently ; ré-entraînement déclenché au-delà d'un seuil configurable.
- **Restitution** : Grafana + source de données PostgreSQL native (trafic, prévision, anomalies, alertes).

## 8. Règles de code (préparent la migration Dagster)

1. Une étape = une **fonction Python pure** paramétrée par `start`, `end` et la config ; le CLI est une couche fine.
2. **Idempotence par fenêtre** : relancer une fenêtre l'écrase sans doublon (`DELETE` de la fenêtre puis `INSERT` dans une même transaction).
3. **Configuration externe** (`.env` / YAML) : connexion PostgreSQL, URI MLflow, seuils. Rien en dur.
4. Table **`ml.runs`** : etape, fenetre_debut, fenetre_fin, statut, nb_lignes, mlflow_run_id, horodatage.
5. **Contrôles de données** (`checks.py`) avant entraînement : fenêtre non vide, taux de nulls, volume plausible.

## 9. Données produites (schéma `ml`)

| Table | Contenu |
|---|---|
| `ml.ground_truth` | scénarios joués |
| `ml.features` | features agrégées par fenêtre |
| `ml.predictions` | prévisions, scores, drapeaux d'anomalie, modèle utilisé |
| `ml.runs` | journal des étapes |

## 10. Structure cible

```
ml/
├── src/trafic_ml/
│   ├── config.py       # lecture .env / YAML
│   ├── db.py           # PostgreSQL : lecture umami, écriture ml
│   ├── features.py     # build_features(start, end)
│   ├── checks.py       # contrôles de données
│   ├── train.py        # train(start, end) -> run MLflow + registre
│   ├── score.py        # score(start, end) avec @champion -> ml.predictions
│   └── drift.py        # rapport Evidently + indicateur de dérive
├── cli.py              # python cli.py <etape> --start ... --end ... | --last 1h
├── sql/                # DDL schéma ml, rôles, vues de features
├── scenarios/          # YAML + graine
├── tests/              # pytest, PostgreSQL et MLflow simulés
├── Makefile            # features, score, drift, train, hourly, daily
├── crontab             # lu par supercronic
└── docker-compose.yml  # PostgreSQL, Umami, MLflow, planificateur, Grafana
```

## 11. Approches considérées

- **A. Comparer plusieurs méthodes** sur le même protocole — **retenue** : montre pourquoi chaque méthode détecte ou rate tel scénario.
- B. Approfondir une seule chaîne (prévision + écart) — pas en v1 ; envisageable ensuite sur la méthode gagnante.
- Stockage : **tout dans PostgreSQL** — retenu (montage le plus simple, volume simulé modeste, Grafana natif). Écartés : Umami en mode ClickHouse (plus lourd, moins documenté) ; Umami sur Postgres + `ml` sur ClickHouse (copie entre bases sans bénéfice pour l'objectif ML).
- Dagster dès la v1 — reporté : coût d'apprentissage hors de l'objectif ML ; le code est écrit pour migrer facilement (§8).

## 12. Feuille de route

1. Scénarios versionnés, `ml.ground_truth`, schéma `ml`, vues de features.
2. Prévision et anomalies, suivi MLflow, scoring horaire via cron.
3. Grafana + alertes, rapport de dérive Evidently, ré-entraînement déclenché.
4. Ensuite : classification de sessions, FastAPI, tests de données, CI, migration Dagster.

**Première tâche** : explorer l'existant (simulateur, docker-compose, version d'Umami, schéma réel de `website_event` / `session`), puis proposer un plan avant de créer le squelette.

## 13. Laissé à l'implémentation

- Granularité exacte (5 min ou 1 h) selon le volume simulé.
- Valeurs des seuils (anomalie, dérive) et de la tolérance d'évaluation.
- Liste précise des features pour Isolation Forest.
- Choix statsforecast ou Prophet après un premier essai.
