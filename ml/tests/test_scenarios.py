from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from trafic_ml.simulator.scenarios import load_plan, load_plan_from_dict

SCENARIOS = __import__("pathlib").Path(__file__).resolve().parents[1] / "scenarios"


def _plan_dict(scenarios):
    return {
        "seed": 1,
        "debut": "2026-01-05T00:00:00Z",
        "fin": "2026-01-12T00:00:00Z",
        "base": {"volume_moyen": 600, "amplitude_jour_nuit": 0.7, "bruit": 0.1,
                 "pages": ["/", "/a"], "referents": ["", "https://google.com"]},
        "scenarios": scenarios,
    }


def test_out_of_range_pic_rejected():
    with pytest.raises(ValidationError):
        load_plan_from_dict(_plan_dict([{"type": "pic", "debut": "2026-01-06T10:00:00Z",
                                         "duree": "PT1H", "facteur": 20}]))


def test_pic_duration_out_of_range_rejected():
    with pytest.raises(ValidationError):
        load_plan_from_dict(_plan_dict([{"type": "pic", "debut": "2026-01-06T10:00:00Z",
                                         "duree": "PT5H", "facteur": 3}]))


def test_bot_share_out_of_range_rejected():
    with pytest.raises(ValidationError):
        load_plan_from_dict(_plan_dict([{"type": "bot", "debut": "2026-01-06T10:00:00Z",
                                         "duree": "PT1H", "part": 0.9}]))


def test_panne_duration_out_of_range_rejected():
    with pytest.raises(ValidationError):
        load_plan_from_dict(_plan_dict([{"type": "panne", "debut": "2026-01-06T10:00:00Z",
                                         "duree": "PT5M"}]))


def test_eval_v1_loads():
    plan = load_plan(SCENARIOS / "eval_v1.yaml")
    assert {s.type for s in plan.scenarios} == {"pic", "bot", "panne", "changement"}
    assert plan.fin - plan.debut == timedelta(days=14)
