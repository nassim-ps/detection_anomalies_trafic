#!/bin/sh
# Rôles du pipeline ML et schéma ml. Exécuté une seule fois par l'initdb de postgres.
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -v reader_pw="$ML_READER_PASSWORD" -v writer_pw="$ML_WRITER_PASSWORD" <<'SQL'
CREATE ROLE ml_reader LOGIN PASSWORD :'reader_pw';
CREATE ROLE ml_writer LOGIN PASSWORD :'writer_pw';
GRANT ml_reader TO ml_writer;
CREATE SCHEMA ml AUTHORIZATION ml_writer;
GRANT USAGE ON SCHEMA ml TO ml_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE ml_writer IN SCHEMA ml GRANT SELECT ON TABLES TO ml_reader;
SQL
