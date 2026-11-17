# Detection d'anomalies de trafic à l'aide de scenarios simulés

Le simulateur joue des scénarios (normal, pic, bot, panne, changement de comportement). Umami collecte les événements dans PostgreSQL. La couche ML détecte ces situations, et la couche MLOps entraîne, versionne, sert et surveille les modèles, puis les ré-entraîne quand le comportement change.

- Spécification : [cdr/spec.md](cdr/spec.md)
- Diagramme de flux : [cdr/diagramme_de_flux.excalidraw](cdr/diagramme_de_flux.excalidraw)

## Démarrage

Prérequis : Docker Desktop, et Python 3.12 (via [uv](https://docs.astral.sh/uv/)) pour lancer les tests depuis l'hôte.

1. **Configuration** : `cp .env.example .env`, puis remplacer chaque `change-me` (les mots de passe `ML_*_PASSWORD` doivent aussi être reportés dans `PG_DSN_*`).
2. **Services** : `docker compose up -d` démarre PostgreSQL (port hôte **5433**), Umami 3.5.0 (`http://localhost:3000`) et la page web (`http://localhost:8080`).
   Au premier démarrage, PostgreSQL crée les rôles `ml_reader` / `ml_writer`, le schéma `ml` et ses tables (`ml/sql/*.sh|*.sql`).
3. **Umami** : se connecter avec `admin` / `umami` et **changer ce mot de passe**. Créer un site (domaine `localhost`), puis reporter son identifiant dans `.env` (`UMAMI_WEBSITE_ID`) et dans `web/index.html`.
4. **Vues de lecture** (une fois, après le premier démarrage d'Umami) :
   ```bash
   MSYS_NO_PATHCONV=1 docker compose exec -T postgres psql -U postgres umami -f /docker-entrypoint-initdb.d/views/20_views.sql
   ```
5. **Simuler le jeu d'évaluation** :
   ```bash
   docker compose run --rm sim python cli.py simulate --plan scenarios/eval_v1.yaml --start 2026-01-05T00:00Z --end 2026-01-19T00:00Z
   ```

## Rejouer une période

Le pipeline n'a pas le droit d'écrire dans les tables d'Umami : les événements déjà envoyés ne peuvent pas être effacés. `ml.ground_truth` est réécrit sans doublon, mais rejouer une fenêtre **double les événements Umami**. Pour repartir de zéro : `docker compose down -v`, puis reprendre le démarrage.

Les tests d'intégration utilisent un plan daté de 2025 (`ml/tests/data_plan_test.yaml`) pour ne jamais toucher la période de `eval_v1` (2026).

## Tests

```bash
cd ml
uv venv --python 3.12 .venv && uv pip install -e ".[dev]" --python .venv/Scripts/python.exe
.venv/Scripts/python -m pytest            # tests unitaires
.venv/Scripts/python -m pytest -m db      # intégration (services docker lancés, vues appliquées)
```
