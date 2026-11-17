-- Tables du schéma ml (propriétaire : ml_writer).
SET ROLE ml_writer;

CREATE TABLE IF NOT EXISTS ml.ground_truth (
    id          bigserial PRIMARY KEY,
    scenario    text        NOT NULL,
    seed        integer     NOT NULL,
    debut       timestamptz NOT NULL,
    fin         timestamptz,            -- NULL pour un changement durable
    parametres  jsonb       NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ground_truth_debut ON ml.ground_truth (debut);

CREATE TABLE IF NOT EXISTS ml.runs (
    id             bigserial PRIMARY KEY,
    etape          text        NOT NULL,
    fenetre_debut  timestamptz NOT NULL,
    fenetre_fin    timestamptz NOT NULL,
    statut         text        NOT NULL CHECK (statut IN ('succes', 'echec')),
    nb_lignes      integer,
    mlflow_run_id  text,
    horodatage     timestamptz NOT NULL DEFAULT now()
);

RESET ROLE;
