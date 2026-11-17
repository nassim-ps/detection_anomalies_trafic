"""Journal des étapes dans ml.runs."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

import psycopg


@dataclass
class Run:
    nb_lignes: int | None = None
    mlflow_run_id: str | None = None


@contextmanager
def track_run(conn: psycopg.Connection, etape: str, start: datetime, end: datetime) -> Iterator[Run]:
    """Écrit une ligne 'succes' (ou 'echec' si une exception remonte, puis la relance)."""
    run = Run()
    statut = "echec"
    try:
        yield run
        statut = "succes"
    finally:
        if conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
            conn.rollback()
        with conn.transaction():
            conn.execute(
                "INSERT INTO ml.runs (etape, fenetre_debut, fenetre_fin, statut, nb_lignes, mlflow_run_id) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (etape, start, end, statut, run.nb_lignes, run.mlflow_run_id),
            )
