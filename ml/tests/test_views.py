from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest

from trafic_ml.simulator.run import simulate

pytestmark = pytest.mark.db
PLAN = Path(__file__).parent / "data_plan_test.yaml"
D0 = datetime(2025, 6, 2, 9, tzinfo=timezone.utc)
D1 = D0 + timedelta(hours=4)
PANNE = (datetime(2025, 6, 2, 12, tzinfo=timezone.utc), datetime(2025, 6, 2, 12, 20, tzinfo=timezone.utc))


@pytest.fixture(scope="module", autouse=True)
def simulated():
    from trafic_ml.config import Settings
    from conftest import ROOT_ENV
    simulate(PLAN, D0, D1, Settings(_env_file=ROOT_ENV))


def test_reader_cannot_write_umami(reader_conn):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        reader_conn.execute("DELETE FROM public.website_event")


def test_reader_cannot_write_ml(reader_conn):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        reader_conn.execute("DELETE FROM ml.ground_truth")


def test_view_counts_match_raw_events(reader_conn, settings):
    wid = settings.umami_website_id
    raw = reader_conn.execute(
        "SELECT count(*) FROM public.website_event WHERE website_id = %s AND event_type = 1 "
        "AND created_at >= %s AND created_at < %s", (wid, D0, D1)).fetchone()[0]
    view = reader_conn.execute(
        "SELECT sum(pages_vues) FROM ml.v_traffic_5m WHERE website_id = %s AND bucket >= %s AND bucket < %s",
        (wid, D0, D1)).fetchone()[0]
    assert raw > 0 and view == raw


def test_view_fills_empty_buckets(reader_conn, settings):
    rows = reader_conn.execute(
        "SELECT pages_vues FROM ml.v_traffic_5m WHERE website_id = %s AND bucket >= %s AND bucket < %s",
        (settings.umami_website_id, *PANNE)).fetchall()
    assert len(rows) == 4
    assert min(r[0] for r in rows) == 0
