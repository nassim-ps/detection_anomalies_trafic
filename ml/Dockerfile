FROM python:3.12-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src

# Développement : code monté en volume, installation éditable + outils de test.
FROM base AS dev
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .
CMD ["python", "cli.py", "--help"]

# Production (image publiée sur Docker Hub) : cible par défaut.
FROM base AS prod
RUN pip install --no-cache-dir .
COPY cli.py ./
COPY sql ./sql
COPY scenarios ./scenarios
ENTRYPOINT ["python", "cli.py"]
CMD ["--help"]
