from datetime import datetime, timezone

import httpx

from trafic_ml.simulator.events import Event
from trafic_ml.simulator.umami import send, to_payload

EVENT = Event(datetime(2025, 6, 2, 10, 0, 5, tzinfo=timezone.utc), "/a", "https://www.google.com/",
              "Mozilla/5.0 test", "10.1.2.3", "fr-FR", "1920x1080", False)


def test_payload_shape():
    body, headers = to_payload(EVENT, "wid", "localhost")
    assert body["type"] == "event"
    p = body["payload"]
    assert p["website"] == "wid" and p["url"] == "/a" and p["hostname"] == "localhost"
    assert p["referrer"] == "https://www.google.com/"
    assert p["timestamp"] == int(EVENT.ts.timestamp())
    assert headers["X-Forwarded-For"] == "10.1.2.3"
    assert headers["User-Agent"] == "Mozilla/5.0 test"


def test_send_counts_only_successes(settings_obj):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(200 if calls["n"] % 2 else 500)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://umami")
    assert send([EVENT] * 4, settings_obj, client) == 2
    assert calls["n"] == 4
