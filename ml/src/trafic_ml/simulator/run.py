"""Étape `simulate` : rejoue un plan vers Umami et journalise la vérité terrain."""
import json
from datetime import datetime
from pathlib import Path

import httpx

from ..config import Settings
from ..db import connect, replace_window
from .events import generate
from .umami import send
from .scenarios import Plan, load_plan


def ground_truth_rows(plan: Plan, start: datetime, end: datetime) -> list[dict]:
    rows = []
    for s in plan.scenarios:
        if start <= s.debut < end:
            fin = s.debut + s.duree if s.duree is not None else None
            params = s.model_dump(mode="json", exclude={"type", "debut", "duree"})
            rows.append({"scenario": s.type, "seed": plan.seed, "debut": s.debut,
                         "fin": fin, "parametres": json.dumps(params)})
    return rows


def simulate(plan_path: Path, start: datetime, end: datetime, settings: Settings) -> int:
    """Envoie les événements de [start, end[ ; retourne le nombre d'événements acceptés."""
    plan = load_plan(plan_path)
    with httpx.Client(base_url=settings.umami_url, timeout=10) as client:
        n = send(generate(plan, start, end), settings, client)
    with connect(settings.pg_dsn_writer) as conn:
        replace_window(conn, "ml.ground_truth", "debut", start, end,
                       ground_truth_rows(plan, start, end))
    return n
