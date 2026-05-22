"""Capture live NHL API JSON payloads to tests/fixtures/ for reproducible tests.

Usage:
    python scripts/capture_fixture.py --game-id 2024020001
    python scripts/capture_fixture.py --date 2024-10-08
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

from nhl_bigquery.client import NHLAPIClient


def capture_game(game_id: int, out_root: Path) -> None:
    client = NHLAPIClient(sleep_seconds=1.0)
    game_dir = out_root / "games" / str(game_id)
    game_dir.mkdir(parents=True, exist_ok=True)
    endpoints = {
        "boxscore": client.get_boxscore,
        "play-by-play": client.get_play_by_play,
        "shift-charts": client.get_shift_charts,
        "right-rail": client.get_right_rail,
        "landing": client.get_landing,
    }
    for name, fn in endpoints.items():
        out = game_dir / f"{name}.json"
        print(f"  {name} -> {out}", flush=True)
        try:
            payload = fn(game_id)
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                print(f"    WARNING: 404 for {name}; saving empty object", flush=True)
                payload = {}
            else:
                raise
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def capture_date(date: str, out_root: Path) -> None:
    client = NHLAPIClient(sleep_seconds=1.0)
    (out_root / "score").mkdir(parents=True, exist_ok=True)
    (out_root / "standings").mkdir(parents=True, exist_ok=True)
    print(f"  score/{date}.json", flush=True)
    (out_root / "score" / f"{date}.json").write_text(
        json.dumps(client.get_score(date), indent=2), encoding="utf-8")
    print(f"  standings/{date}.json", flush=True)
    (out_root / "standings" / f"{date}.json").write_text(
        json.dumps(client.get_standings(date), indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-id", type=int)
    parser.add_argument("--date", type=str)
    parser.add_argument("--out", type=Path, default=Path("tests/fixtures"))
    ns = parser.parse_args(argv)

    if not ns.game_id and not ns.date:
        parser.error("provide --game-id or --date")

    if ns.game_id:
        print(f"Capturing game {ns.game_id} -> {ns.out}", flush=True)
        capture_game(ns.game_id, ns.out)
    if ns.date:
        print(f"Capturing date {ns.date} -> {ns.out}", flush=True)
        capture_date(ns.date, ns.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
