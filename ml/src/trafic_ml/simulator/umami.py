"""Envoi des événements à l'API de collecte d'Umami (POST /api/send). Jamais d'écriture directe en base."""
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable

import httpx

from ..config import Settings
from .events import Event

MAX_WORKERS = 16


def to_payload(e: Event, website_id: str, hostname: str) -> tuple[dict, dict]:
    body = {
        "type": "event",
        "payload": {
            "website": website_id,
            "hostname": hostname,
            "url": e.url,
            "referrer": e.referrer,
            "language": e.language,
            "screen": e.screen,
            "title": e.url,
            "timestamp": int(e.ts.timestamp()),
        },
    }
    # Umami déduit la session de l'IP et du user-agent : une IP par visiteur simulé.
    headers = {"User-Agent": e.user_agent, "X-Forwarded-For": e.ip}
    return body, headers


def send(events: Iterable[Event], settings: Settings, client: httpx.Client,
         hostname: str = "localhost") -> int:
    """Envoie les événements ; retourne le nombre d'envois acceptés (HTTP 2xx)."""
    def one(e: Event) -> bool:
        body, headers = to_payload(e, settings.umami_website_id, hostname)
        try:
            return client.post("/api/send", json=body, headers=headers).is_success
        except httpx.HTTPError:
            return False

    with ThreadPoolExecutor(MAX_WORKERS) as pool:
        return sum(pool.map(one, events))
