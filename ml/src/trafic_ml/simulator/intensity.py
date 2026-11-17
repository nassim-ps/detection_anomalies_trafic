"""Taux d'événements attendu (sans aléa) à l'instant t."""
import math
from datetime import datetime

from .scenarios import Bot, Changement, Panne, Pic, Plan

WEEKEND_FACTOR = 0.8
PANNE_FACTOR = 0.01


def _base_rate(t: datetime, plan: Plan) -> float:
    b = plan.base
    heure = t.hour + t.minute / 60
    # minimum vers 4 h, maximum vers 16 h
    jour = 1 + b.amplitude_jour_nuit * math.cos(2 * math.pi * (heure - 16) / 24)
    semaine = WEEKEND_FACTOR if t.weekday() >= 5 else 1.0
    return b.volume_moyen * jour * semaine


def intensity(t: datetime, plan: Plan) -> tuple[float, float]:
    """(taux humain, taux bot) en événements par heure."""
    humain, bot = _base_rate(t, plan), 0.0
    actifs = plan.actifs(t)
    for s in actifs:
        if isinstance(s, Changement):
            humain *= 1 + s.ampleur
        elif isinstance(s, Pic):
            humain *= s.facteur
    for s in actifs:
        if isinstance(s, Bot):
            bot += humain * s.part / (1 - s.part)
    if any(isinstance(s, Panne) for s in actifs):
        humain, bot = humain * PANNE_FACTOR, bot * PANNE_FACTOR
    return humain, bot
