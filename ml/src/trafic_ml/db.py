"""Accès PostgreSQL : lecture via les vues ml.*, écriture idempotente dans le schéma ml uniquement."""
from datetime import datetime

import psycopg
from psycopg import sql

# Garde-fou : le pipeline n'écrit jamais ailleurs que dans ces tables.
WRITABLE_TABLES = {"ml.ground_truth", "ml.runs", "ml.features", "ml.predictions"}


def connect(dsn: str) -> psycopg.Connection:
    return psycopg.connect(dsn)


def replace_window(conn: psycopg.Connection, table: str, time_col: str,
                   start: datetime, end: datetime, rows: list[dict]) -> int:
    """Supprime les lignes où start <= time_col < end puis insère rows, dans une transaction."""
    if table not in WRITABLE_TABLES:
        raise ValueError(f"écriture interdite dans {table}")
    schema, name = table.split(".")
    ident = sql.Identifier(schema, name)
    with conn.transaction():
        conn.execute(
            sql.SQL("DELETE FROM {} WHERE {} >= %s AND {} < %s").format(
                ident, sql.Identifier(time_col), sql.Identifier(time_col)),
            (start, end),
        )
        if rows:
            cols = list(rows[0])
            stmt = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                ident,
                sql.SQL(", ").join(map(sql.Identifier, cols)),
                sql.SQL(", ").join(sql.Placeholder() * len(cols)),
            )
            with conn.cursor() as cur:
                cur.executemany(stmt, [tuple(r[c] for c in cols) for r in rows])
    return len(rows)
