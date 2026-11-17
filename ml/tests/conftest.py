from pathlib import Path

import pytest

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


@pytest.fixture
def settings():
    from trafic_ml.config import Settings
    return Settings(_env_file=ROOT_ENV)


@pytest.fixture
def conn(settings):
    from trafic_ml.db import connect
    c = connect(settings.pg_dsn_writer)
    c.execute("TRUNCATE ml.ground_truth, ml.runs")
    c.commit()
    yield c
    c.close()


@pytest.fixture
def reader_conn(settings):
    from trafic_ml.db import connect
    c = connect(settings.pg_dsn_reader)
    yield c
    c.rollback()
    c.close()


@pytest.fixture
def settings_obj():
    from trafic_ml.config import Settings
    return Settings(_env_file=None, pg_dsn_reader="x", pg_dsn_writer="x",
                    umami_url="http://umami", umami_website_id="wid")
