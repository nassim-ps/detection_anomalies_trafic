from datetime import datetime, timedelta, timezone

import pytest

from trafic_ml.simulator.intensity import intensity
from trafic_ml.simulator.scenarios import load_plan_from_dict

D0 = datetime(2026, 1, 5, tzinfo=timezone.utc)  # lundi
H = timedelta(hours=1)


def plan(*scenarios):
    return load_plan_from_dict({
        "seed": 1, "debut": D0, "fin": D0 + timedelta(days=14),
        "base": {"volume_moyen": 600, "amplitude_jour_nuit": 0.7, "bruit": 0.1,
                 "pages": ["/", "/a", "/b"], "referents": [""]},
        "scenarios": list(scenarios),
    })


def at(hhmm, day=1):
    h, m = map(int, hhmm.split(":"))
    return D0 + timedelta(days=day, hours=h, minutes=m)


def test_night_lower_than_day():
    p = plan()
    assert intensity(at("03:00"), p)[0] < intensity(at("15:00"), p)[0]


def test_pic_multiplies_rate():
    p = plan({"type": "pic", "debut": at("10:00"), "duree": "PT1H", "facteur": 3})
    assert intensity(at("10:30"), p)[0] == pytest.approx(3 * intensity(at("10:30"), plan())[0])
    assert intensity(at("11:30"), p) == intensity(at("11:30"), plan())


def test_panne_near_zero():
    p = plan({"type": "panne", "debut": at("10:00"), "duree": "PT1H"})
    assert sum(intensity(at("10:30"), p)) < 0.05 * intensity(at("10:30"), plan())[0]


def test_bot_share():
    p = plan({"type": "bot", "debut": at("10:00"), "duree": "PT1H", "part": 0.3})
    h, b = intensity(at("10:30"), p)
    assert b / (h + b) == pytest.approx(0.3)
    assert h == pytest.approx(intensity(at("10:30"), plan())[0])


def test_changement_persists():
    p = plan({"type": "changement", "debut": at("00:00", day=3), "ampleur": 0.5, "pages": ["/b"]})
    assert intensity(at("15:00", day=13), p) != intensity(at("15:00", day=13), plan())
    assert intensity(at("15:00", day=2), p) == intensity(at("15:00", day=2), plan())
