"""Scénarios du simulateur : modèles validés et chargement YAML (bornes : spec §4)."""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal, Union

import yaml
from pydantic import AwareDatetime, BaseModel, Field, field_validator


class Base(BaseModel):
    volume_moyen: float = Field(gt=0, description="pages vues / heure en moyenne")
    amplitude_jour_nuit: float = Field(ge=0, le=1)
    bruit: float = Field(ge=0, le=1)
    pages: list[str] = Field(min_length=1)
    referents: list[str] = Field(min_length=1)


def _check_duration(v: timedelta, lo: timedelta, hi: timedelta) -> timedelta:
    if not lo <= v <= hi:
        raise ValueError(f"durée hors bornes [{lo}, {hi}]")
    return v


class Pic(BaseModel):
    type: Literal["pic"]
    debut: AwareDatetime
    duree: timedelta
    facteur: float = Field(ge=3, le=10)

    @field_validator("duree")
    @classmethod
    def _duree(cls, v):
        return _check_duration(v, timedelta(minutes=15), timedelta(hours=2))


class Bot(BaseModel):
    type: Literal["bot"]
    debut: AwareDatetime
    duree: timedelta
    part: float = Field(ge=0.10, le=0.50)


class Panne(BaseModel):
    type: Literal["panne"]
    debut: AwareDatetime
    duree: timedelta

    @field_validator("duree")
    @classmethod
    def _duree(cls, v):
        return _check_duration(v, timedelta(minutes=10), timedelta(hours=3))


class Changement(BaseModel):
    """Nouveau régime durable à partir de `debut`."""
    type: Literal["changement"]
    debut: AwareDatetime
    ampleur: float = Field(gt=-1, le=2, description="variation relative du volume")
    pages: list[str] = Field(min_length=1, description="pages favorisées après la bascule")

    @property
    def duree(self) -> None:
        return None


Scenario = Annotated[Union[Pic, Bot, Panne, Changement], Field(discriminator="type")]


class Plan(BaseModel):
    seed: int
    debut: AwareDatetime
    fin: AwareDatetime
    base: Base
    scenarios: list[Scenario] = []

    def actifs(self, t: datetime) -> list:
        out = []
        for s in self.scenarios:
            if isinstance(s, Changement):
                if t >= s.debut:
                    out.append(s)
            elif s.debut <= t < s.debut + s.duree:
                out.append(s)
        return out


def load_plan_from_dict(data: dict) -> Plan:
    return Plan.model_validate(data)


def load_plan(path: Path) -> Plan:
    with open(path, encoding="utf-8") as f:
        return load_plan_from_dict(yaml.safe_load(f))
