"""Génération déterministe des événements : même plan + même graine => mêmes événements.

Chaque minute a son propre générateur aléatoire (graine = [plan.seed, minute]),
ce qui rend une sous-fenêtre identique à la même période d'une fenêtre plus large.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterator

import numpy as np

from .intensity import intensity
from .scenarios import Changement, Plan

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36 Edg/130.0",
]
BOT_USER_AGENTS = [
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "python-requests/2.32.3",
]
LANGUAGES = ["fr-FR", "fr-FR", "fr-FR", "en-US", "en-GB", "de-DE", "es-ES"]
SCREENS = ["1920x1080", "1366x768", "1536x864", "2560x1440", "390x844", "412x915", "768x1024"]

PAGES_PAR_VISITE = (1, 6)        # bornes incluses
DELAI_MOYEN_S = 40.0             # délai moyen entre deux pages d'une visite
LOOKBACK = timedelta(hours=1)    # visites commencées avant la fenêtre mais encore actives
CHANGEMENT_PART_PAGES = 0.5      # part des pages tirées dans les pages favorisées


@dataclass(frozen=True)
class Event:
    ts: datetime
    url: str
    referrer: str
    user_agent: str
    ip: str
    language: str
    screen: str
    is_bot: bool


def _pages(plan: Plan, t: datetime) -> tuple[list[str], list[str]]:
    fav: list[str] = []
    for s in plan.actifs(t):
        if isinstance(s, Changement):
            fav = s.pages
    return plan.base.pages, fav


def _minute_events(plan: Plan, t0: datetime, minute: int) -> list[Event]:
    rng = np.random.default_rng([plan.seed, minute])
    humain, bot = intensity(t0, plan)
    sigma = plan.base.bruit
    bruit = rng.lognormal(-sigma**2 / 2, sigma) if sigma > 0 else 1.0
    lo, hi = PAGES_PAR_VISITE
    pages_moy = (lo + hi) / 2
    base_pages, fav = _pages(plan, t0)
    out: list[Event] = []

    for _ in range(rng.poisson(humain / 60 / pages_moy * bruit)):
        ts = t0 + timedelta(seconds=float(rng.uniform(0, 60)))
        ip = f"10.{rng.integers(0, 256)}.{rng.integers(0, 256)}.{rng.integers(1, 255)}"
        ua = USER_AGENTS[rng.integers(len(USER_AGENTS))]
        lang = LANGUAGES[rng.integers(len(LANGUAGES))]
        screen = SCREENS[rng.integers(len(SCREENS))]
        ref = plan.base.referents[rng.integers(len(plan.base.referents))]
        for _ in range(int(rng.integers(lo, hi + 1))):
            pool = fav if fav and rng.random() < CHANGEMENT_PART_PAGES else base_pages
            out.append(Event(ts, pool[rng.integers(len(pool))], ref, ua, ip, lang, screen, False))
            ref = ""  # référent seulement sur la première page
            ts += timedelta(seconds=float(rng.exponential(DELAI_MOYEN_S)))

    n_bot = int(round(bot / 60))
    for i in range(n_bot):
        ts = t0 + timedelta(seconds=60 * (i + 0.5) / n_bot)
        url = base_pages[(minute * n_bot + i) % len(base_pages)]
        out.append(Event(ts, url, "", BOT_USER_AGENTS[minute % len(BOT_USER_AGENTS)], "10.250.0.1",
                         "en-US", "1920x1080", True))
    return out


def generate(plan: Plan, start: datetime, end: datetime) -> Iterator[Event]:
    """Événements dont l'horodatage est dans [start, end[, triés."""
    first = max(0, int((start - LOOKBACK - plan.debut).total_seconds() // 60))  # rien avant le plan
    last = int((end - plan.debut).total_seconds() // 60)
    evs: list[Event] = []
    for m in range(first, last + 1):
        t0 = plan.debut + timedelta(minutes=m)
        evs.extend(e for e in _minute_events(plan, t0, m) if start <= e.ts < end)
    evs.sort(key=lambda e: (e.ts, e.ip, e.url))
    yield from evs
