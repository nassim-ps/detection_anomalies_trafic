# Détection d'anomalies de trafic sur scénarios simulés

Un simulateur rejoue des scénarios (normal, pic, bot, panne, changement de comportement) vers **Umami**, qui stocke tout dans **PostgreSQL**. La couche ML apprend à les détecter.

[Spécification](cdr/spec.md) · [Diagramme de flux](cdr/diagramme_de_flux.excalidraw)

## Installation rapide

Prérequis : Docker. Il faut seulement [`compose.prod.yml`](compose.prod.yml) et un `.env` (modèle : [`.env.example`](.env.example)).

```bash
cp .env.example .env                          # remplacer chaque change-me
docker compose -f compose.prod.yml up -d      # PostgreSQL :5433, Umami :3000, puis init de la base
```

Sur Umami (`http://localhost:3000`) :

1. Se connecter avec `admin` / `umami`, puis changer ce mot de passe.
2. Créer un site.
3. Reporter son identifiant dans `.env` (`UMAMI_WEBSITE_ID`).

Ensuite, jouer le jeu d'évaluation :

```bash
docker compose -f compose.prod.yml run --rm sim simulate \
  --plan scenarios/eval_v1.yaml --start 2026-01-05T00:00Z --end 2026-01-19T00:00Z
```

> Rejouer une période **double les événements dans Umami**, car le pipeline n'y écrit jamais. Pour repartir de zéro : `docker compose -f compose.prod.yml down -v`.

## Développement

```bash
docker compose up -d                          # même pile, image construite depuis ./ml + page web :8080
docker compose run --rm sim python cli.py simulate --plan ... --start ... --end ...

cd ml && uv venv --python 3.12 .venv && uv pip install -e ".[dev]" --python .venv/Scripts/python.exe
.venv/Scripts/python -m pytest                # unitaires
.venv/Scripts/python -m pytest -m db          # intégration (pile docker lancée)
```

## Image et CI

La CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) lance les tests, puis publie l'image sur `nassimphenix/detection-anomalies-trafic` :

- sur un push vers `main`, avec les tags `latest` et `sha-…` ;
- sur une pull request vers `main`, avec le tag `pr-N`.

Pour que la CI puisse publier, déclarer dans GitHub (Settings → Secrets and variables → Actions) :

- la variable `DOCKERHUB_USERNAME` ;
- le secret `DOCKERHUB_TOKEN`.
