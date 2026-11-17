from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from trafic_ml.simulator.run import simulate

pytestmark = pytest.mark.db
PLAN = Path(__file__).parent / "data_plan_test.yaml"
D0 = datetime(2025, 6, 2, 9, tzinfo=timezone.utc)


def test_simulate_writes_ground_truth_idempotently(settings, conn):
    n = simulate(PLAN, D0, D0 + timedelta(hours=4), settings)
    assert n > 0
    simulate(PLAN, D0, D0 + timedelta(hours=4), settings)  # rejoué
    rows = conn.execute("SELECT scenario, debut, fin FROM ml.ground_truth ORDER BY debut").fetchall()
    assert [r[0] for r in rows] == ["pic", "panne"]
    assert rows[0][2] - rows[0][1] == timedelta(minutes=30)


def test_simulate_logs_run(settings, conn):
    n = simulate(PLAN, D0, D0 + timedelta(hours=1), settings)
    assert conn.execute(
        "SELECT etape, statut, nb_lignes FROM ml.runs ORDER BY id DESC LIMIT 1").fetchone() == ("simulate", "succes", n)
