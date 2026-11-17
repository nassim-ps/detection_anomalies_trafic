#!/bin/sh
# Initialise la base pour le pipeline : rôles, schéma ml, tables, vues de lecture.
# Lancé par le service `init` une fois Umami démarré (ses tables doivent exister). Idempotent.
set -eu
: "${ML_READER_PASSWORD:?ML_READER_PASSWORD manquant}"
: "${ML_WRITER_PASSWORD:?ML_WRITER_PASSWORD manquant}"
cd "$(dirname "$0")"
psql -v ON_ERROR_STOP=1 -v reader_pw="$ML_READER_PASSWORD" -v writer_pw="$ML_WRITER_PASSWORD" -f 00_roles.sql
psql -v ON_ERROR_STOP=1 -f 10_tables.sql
psql -v ON_ERROR_STOP=1 -f views/20_views.sql
echo "init: base prête"
