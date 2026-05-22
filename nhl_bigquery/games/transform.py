"""Games transform: /score/{date} → rows; /landing/{id} → enrichment row."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

_GAME_TYPE_MAP = {1: "PR", 2: "R", 3: "P", 4: "AS"}


def transform_score_to_games_rows(score_resp: dict[str, Any], *, date: str) -> pd.DataFrame:
    """Convert /score/{date} response to bare games rows (no landing enrichment)."""
    ingested_at = datetime.now(timezone.utc)
    rows = []
    for g in score_resp.get("games", []):
        game_type_int = int(g.get("gameType") or 2)
        season_raw = int(g.get("season") or 0)
        rows.append({
            "game_id": int(g["id"]),
            "game_date": g.get("gameDate") or date,
            "season": season_raw // 10000,
            "game_type": _GAME_TYPE_MAP.get(game_type_int),
            "home_team_id": int(g.get("homeTeam", {}).get("id")),
            "away_team_id": int(g.get("awayTeam", {}).get("id")),
            "home_team_abbrev": g.get("homeTeam", {}).get("abbrev"),
            "away_team_abbrev": g.get("awayTeam", {}).get("abbrev"),
            "venue_default_name": (g.get("venue") or {}).get("default"),
            "start_time_utc": g.get("startTimeUTC"),
            "eastern_utc_offset": g.get("easternUTCOffset"),
            "venue_utc_offset": g.get("venueUTCOffset"),
            "game_state": g.get("gameState"),
            "final_period_type": None,
            "home_score_final": (g.get("homeTeam") or {}).get("score"),
            "away_score_final": (g.get("awayTeam") or {}).get("score"),
            "is_shootout_decided": None,
            "ingested_at": ingested_at,
        })
    return pd.DataFrame(rows)


def transform_landing_to_games_row(landing: dict[str, Any]) -> dict[str, Any]:
    """Convert /gamecenter/{id}/landing response to a single enrichment row."""
    outcome = landing.get("gameOutcome") or {}
    last_period = outcome.get("lastPeriodType")
    home = landing.get("homeTeam") or {}
    away = landing.get("awayTeam") or {}
    game_type_int = int(landing.get("gameType") or 2)
    season_raw = int(landing.get("season") or 0)
    return {
        "game_id": int(landing["id"]),
        "game_date": landing.get("gameDate"),
        "season": season_raw // 10000,
        "game_type": _GAME_TYPE_MAP.get(game_type_int),
        "home_team_id": int(home.get("id")),
        "away_team_id": int(away.get("id")),
        "home_team_abbrev": home.get("abbrev"),
        "away_team_abbrev": away.get("abbrev"),
        "venue_default_name": (landing.get("venue") or {}).get("default"),
        "start_time_utc": landing.get("startTimeUTC"),
        "eastern_utc_offset": landing.get("easternUTCOffset"),
        "venue_utc_offset": landing.get("venueUTCOffset"),
        "game_state": landing.get("gameState"),
        "final_period_type": last_period,
        "home_score_final": home.get("score"),
        "away_score_final": away.get("score"),
        "is_shootout_decided": last_period == "SO" if last_period else None,
        "ingested_at": datetime.now(timezone.utc),
    }
