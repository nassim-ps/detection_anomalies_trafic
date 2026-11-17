"""Couche fine autour des étapes : python cli.py <etape> --start ... --end ... | --last 1h"""
import argparse
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from trafic_ml.config import get_settings

_UNITS = {"m": "minutes", "h": "hours", "d": "days"}


def _dt(s: str) -> datetime:
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def parse_window(args: argparse.Namespace, now: datetime | None = None) -> tuple[datetime, datetime]:
    if args.last:
        m = re.fullmatch(r"(\d+)([mhd])", args.last)
        if not m:
            raise SystemExit("--last attend par ex. 30m, 1h, 7d")
        end = now or datetime.now(timezone.utc)
        return end - timedelta(**{_UNITS[m[2]]: int(m[1])}), end
    if not (args.start and args.end):
        raise SystemExit("préciser --start et --end, ou --last")
    start, end = _dt(args.start), _dt(args.end)
    if start >= end:
        raise SystemExit("--start doit précéder --end")
    return start, end


def _window_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--start")
    p.add_argument("--end")
    p.add_argument("--last")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="cli.py")
    sub = parser.add_subparsers(dest="etape", required=True)
    sim = sub.add_parser("simulate", help="rejoue un plan de scénarios vers Umami")
    sim.add_argument("--plan", required=True, type=Path)
    _window_args(sim)
    args = parser.parse_args(argv)

    start, end = parse_window(args)
    if args.etape == "simulate":
        from trafic_ml.simulator.run import simulate
        n = simulate(args.plan, start, end, get_settings())
        print(f"simulate: {n} événements envoyés pour [{start}, {end}[")


if __name__ == "__main__":
    main()
