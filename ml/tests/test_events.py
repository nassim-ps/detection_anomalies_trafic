from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from trafic_ml.simulator.events import generate
from trafic_ml.simulator.intensity import intensity
from trafic_ml.simulator.scenarios import load_plan_from_dict

D0 = datetime(2026, 1, 5, tzinfo=timezone.utc)
DAY = timedelta(days=1)


def plan(*scenarios, seed=1):
    return load_plan_from_dict({
        "seed": seed, "debut": D0, "fin": D0 + 14 * DAY,
        "base": {"volume_moyen": 300, "amplitude_jour_nuit": 0.7, "bruit": 0.1,
                 "pages": ["/", "/a", "/b", "/c"],
                 "referents": ["", "https://www.google.com/", "https://www.bing.com/", "https://t.co/"]},
        "scenarios": list(scenarios),
    })


def test_same_seed_same_events():
    p = plan()
    assert list(generate(p, D0, D0 + DAY)) == list(generate(p, D0, D0 + DAY))


def test_different_seed_different_events():
    assert list(generate(plan(), D0, D0 + DAY)) != list(generate(plan(seed=2), D0, D0 + DAY))


def test_sub_window_is_consistent_with_full_window():
    p = plan()
    full = [e for e in generate(p, D0, D0 + 2 * DAY) if e.ts >= D0 + DAY]
    assert list(generate(p, D0 + DAY, D0 + 2 * DAY)) == full


def test_sorted_and_within_window():
    evs = list(generate(plan(), D0, D0 + DAY))
    ts = [e.ts for e in evs]
    assert ts == sorted(ts) and ts[0] >= D0 and ts[-1] < D0 + DAY


def test_counts_follow_intensity():
    p = plan()
    n = sum(1 for _ in generate(p, D0, D0 + 7 * DAY))
    expected = sum(intensity(D0 + timedelta(minutes=m), p)[0] / 60 for m in range(7 * 24 * 60))
    assert n == pytest.approx(expected, rel=0.10)


def test_visitors_have_distinct_ips():
    humans = [e for e in generate(plan(), D0, D0 + DAY) if not e.is_bot]
    assert len({e.ip for e in humans}) > 0.5 * len({(e.ip, e.user_agent) for e in humans})


def test_bots_homogeneous_and_regular():
    p = plan({"type": "bot", "debut": D0 + timedelta(hours=10), "duree": "PT2H", "part": 0.3})
    bots = [e for e in generate(p, D0, D0 + DAY) if e.is_bot]
    assert len(bots) > 50
    assert len({e.user_agent for e in bots}) <= 2
    assert all(e.referrer == "" for e in bots)
    gaps = np.diff([e.ts.timestamp() for e in bots[:50]])
    assert gaps.std() < 0.2 * gaps.mean()


def test_humans_varied():
    humans = [e for e in generate(plan(), D0, D0 + DAY) if not e.is_bot]
    assert len({e.user_agent for e in humans}) >= 5
    assert len({e.referrer for e in humans}) >= 3


def test_changement_shifts_pages():
    p = plan({"type": "changement", "debut": D0 + 3 * DAY, "ampleur": 0.0, "pages": ["/c"]})
    before = [e.url for e in generate(p, D0, D0 + DAY)]
    after = [e.url for e in generate(p, D0 + 4 * DAY, D0 + 5 * DAY)]
    assert after.count("/c") / len(after) > 2 * before.count("/c") / len(before)
