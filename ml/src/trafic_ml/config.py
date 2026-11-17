"""Configuration externe : lue depuis l'environnement ou un fichier .env."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ML_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    pg_dsn_reader: str
    pg_dsn_writer: str
    umami_url: str
    umami_website_id: str
    scenarios_dir: Path = _ML_ROOT / "scenarios"


def get_settings() -> Settings:
    return Settings()
