from datetime import datetime, timedelta, timezone

import pytest

from trafic_ml.runs import track_run

pytestmark = pytest.mark.db
A = datetime(2026, 1, 5, tzinfo=timezone.utc)
B = A + timedelta(hours=1)


def last_run(conn):
    return conn.execute(
        "SELECT etape, statut, nb_lignes, fenetre_debut, fenetre_fin FROM ml.runs ORDER BY id DESC LIMIT 1"
    ).fetchone()


def test_track_run_success(conn):
    with track_run(conn, "simulate", A, B) as run:
        run.nb_lignes = 42
    assert last_run(conn) == ("simulate", "succes", 42, A, B)


def test_track_run_failure_recorded_and_reraised(conn):
    with pytest.raises(RuntimeError):
        with track_run(conn, "simulate", A, B):
            raise RuntimeError("boom")
    assert last_run(conn)[:2] == ("simulate", "echec")
