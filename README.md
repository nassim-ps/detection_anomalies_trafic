# Detection d'anomalies de trafic à l'aide de scenarios simulés

Le simulateur joue des scénarios (normal, pic, bot, panne, changement de comportement). Umami collecte les événements dans PostgreSQL. La couche ML détecte ces situations, et la couche MLOps entraîne, versionne, sert et surveille les modèles, puis les ré-entraîne quand le comportement change.

[Spec](cdr/spec.md) · [Flux](cdr/diagramme_de_flux.excalidraw)

## Installer

```bash
cp .env.example .env    # remplacer les change-me
docker compose -f compose.prod.yml up -d
```

Sur http://localhost:3000, se connecter avec `admin` / `umami`, puis :

1. Changer le mot de passe.
2. Créer un site.
3. Copier son identifiant dans `UMAMI_WEBSITE_ID` du `.env`.

## Simuler

```bash
docker compose -f compose.prod.yml run --rm sim simulate --plan scenarios/eval_v1.yaml --start 2026-01-05T00:00Z --end 2026-01-19T00:00Z
```

Rejouer une période duplique les événements. Pour tout effacer : `docker compose -f compose.prod.yml down -v`.

## Développer

```bash
docker compose up -d
cd ml && uv venv --python 3.12 .venv && uv pip install -e ".[dev]" --python .venv/Scripts/python.exe
.venv/Scripts/python -m pytest          # unitaires
.venv/Scripts/python -m pytest -m db    # intégration
```

## CI

À chaque push ou PR vers `main`, la CI lance les tests puis publie l'image `nassimphenix/detection-anomalies-trafic`. Elle a besoin, dans GitHub, de la variable `DOCKERHUB_USERNAME` et du secret `DOCKERHUB_TOKEN`.
