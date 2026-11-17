import json
from datetime import datetime, timedelta, timezone

import pytest

from trafic_ml.db import replace_window

pytestmark = pytest.mark.db

T0 = datetime(2026, 1, 5, tzinfo=timezone.utc)
H, DAY = timedelta(hours=1), timedelta(days=1)


def row_at(t):
    return {"scenario": "pic", "seed": 1, "debut": t, "fin": t + H, "parametres": json.dumps({})}


def count(conn, table):
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_replace_window_is_idempotent(conn):
    rows = [row_at(T0)]
    assert replace_window(conn, "ml.ground_truth", "debut", T0, T0 + DAY, rows) == 1
    replace_window(conn, "ml.ground_truth", "debut", T0, T0 + DAY, rows)
    assert count(conn, "ml.ground_truth") == 1


def test_replace_window_keeps_other_windows(conn):
    replace_window(conn, "ml.ground_truth", "debut", T0, T0 + DAY, [row_at(T0)])
    replace_window(conn, "ml.ground_truth", "debut", T0 + DAY, T0 + 2 * DAY, [row_at(T0 + DAY)])
    assert count(conn, "ml.ground_truth") == 2


def test_replace_window_rejects_unknown_table(conn):
    with pytest.raises(ValueError):
        replace_window(conn, "public.website_event", "created_at", T0, T0 + DAY, [])


def test_replace_window_rolls_back_on_error(conn):
    replace_window(conn, "ml.ground_truth", "debut", T0, T0 + DAY, [row_at(T0)])
    with pytest.raises(Exception):
        replace_window(conn, "ml.ground_truth", "debut", T0, T0 + DAY, [{"colonne_inconnue": 1}])
    assert count(conn, "ml.ground_truth") == 1
