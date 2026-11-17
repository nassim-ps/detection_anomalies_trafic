import pytest
from pydantic import ValidationError

from trafic_ml.config import Settings, get_settings


def test_settings_read_from_env(monkeypatch):
    monkeypatch.setenv("PG_DSN_READER", "postgresql://r@h/db")
    monkeypatch.setenv("PG_DSN_WRITER", "postgresql://w@h/db")
    monkeypatch.setenv("UMAMI_URL", "http://umami:3000")
    monkeypatch.setenv("UMAMI_WEBSITE_ID", "00000000-0000-0000-0000-000000000000")
    s = get_settings()
    assert s.pg_dsn_writer == "postgresql://w@h/db"
    assert s.scenarios_dir.name == "scenarios"


def test_settings_missing_var_fails(monkeypatch):
    for v in ("PG_DSN_READER", "PG_DSN_WRITER", "UMAMI_URL", "UMAMI_WEBSITE_ID"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
