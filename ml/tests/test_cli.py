import argparse
from datetime import datetime, timedelta, timezone

import pytest

from cli import parse_window

NOW = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)


def ns(**kw):
    return argparse.Namespace(**{"start": None, "end": None, "last": None, **kw})


def test_last_hour():
    assert parse_window(ns(last="1h"), NOW) == (NOW - timedelta(hours=1), NOW)


def test_explicit_window_defaults_to_utc():
    s, e = parse_window(ns(start="2026-01-05T00:00", end="2026-01-06T00:00"))
    assert s.tzinfo is not None and e - s == timedelta(days=1)


@pytest.mark.parametrize("kw", [{"last": "1y"}, {"start": "2026-01-05"}, {"start": "2026-01-06", "end": "2026-01-05"}])
def test_invalid_windows_rejected(kw):
    with pytest.raises(SystemExit):
        parse_window(ns(**kw), NOW)
