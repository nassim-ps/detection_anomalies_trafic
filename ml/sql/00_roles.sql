-- Rôles du pipeline ML et schéma ml. Idempotent : rejouable à chaque démarrage.
-- Variables psql attendues : reader_pw, writer_pw.
SELECT 'CREATE ROLE ml_reader LOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ml_reader') \gexec
SELECT 'CREATE ROLE ml_writer LOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ml_writer') \gexec
ALTER ROLE ml_reader PASSWORD :'reader_pw';
ALTER ROLE ml_writer PASSWORD :'writer_pw';
GRANT ml_reader TO ml_writer;
CREATE SCHEMA IF NOT EXISTS ml AUTHORIZATION ml_writer;
GRANT USAGE ON SCHEMA ml TO ml_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE ml_writer IN SCHEMA ml GRANT SELECT ON TABLES TO ml_reader;
