"""Boxscore transform: /gamecenter/{id}/boxscore → per-player rows (skater + goalie)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


_SKATER_FIELDS = (
    "goals", "assists", "points", "plusMinus", "pim", "hits", "blockedShots",
    "shots", "faceoffs", "faceoffWinningPctg",
    "powerPlayGoals", "powerPlayPoints", "shorthandedGoals", "shPoints",
    "powerPlayToi", "shorthandedToi",
)

_GOALIE_FIELDS = (
    "saveShotsAgainst", "goalsAgainst", "savePctg",
    "evenStrengthShotsAgainst", "powerPlayShotsAgainst", "shorthandedShotsAgainst",
    "evenStrengthGoalsAgainst", "powerPlayGoalsAgainst", "shorthandedGoalsAgainst",
)


def _camel_to_snake(s: str) -> str:
    out = []
    for c in s:
        if c.isupper():
            out.append("_" + c.lower())
        else:
            out.append(c)
    return "".join(out).lstrip("_")


def transform_boxscore_to_df(bs: dict[str, Any]) -> pd.DataFrame:
    """Extract per-player per-game rows from a boxscore response."""
    game_id = int(bs["id"])
    game_date = bs.get("gameDate")
    pgs = bs.get("playerByGameStats") or {}
    rows: list[dict[str, Any]] = []
    ingested_at = datetime.now(timezone.utc)

    for side in ("awayTeam", "homeTeam"):
        team_id = int((bs.get(side) or {}).get("id"))
        side_block = pgs.get(side) or {}
        for cat, players in (
            ("skater", side_block.get("forwards") or []),
            ("skater", side_block.get("defense") or []),
            ("goalie", side_block.get("goalies") or []),
        ):
            for p in players:
                row: dict[str, Any] = {
                    "game_id": game_id,
                    "game_date": game_date,
                    "player_id": int(p["playerId"]),
                    "team_id": team_id,
                    "player_position_category": cat,
                    "position_code": p.get("position"),
                    "sweater_number": p.get("sweaterNumber"),
                    "toi": p.get("toi"),
                    "ingested_at": ingested_at,
                }
                # Skater fields
                for f in _SKATER_FIELDS:
                    row[_camel_to_snake(f)] = p.get(f)
                # Goalie fields (with renames)
                # saveShotsAgainst may be "saves/shots" string (e.g. "19/22") or numeric
                save_shots_raw = p.get("saveShotsAgainst")
                goals_against = p.get("goalsAgainst")
                shots_against_int = p.get("shotsAgainst")
                saves_int = p.get("saves")
                # Parse "saves/shots" string format if needed
                if isinstance(save_shots_raw, str) and "/" in save_shots_raw:
                    parts = save_shots_raw.split("/")
                    try:
                        saves_int = saves_int if saves_int is not None else int(parts[0])
                        shots_against_int = shots_against_int if shots_against_int is not None else int(parts[1])
                    except (ValueError, IndexError):
                        pass
                elif isinstance(save_shots_raw, (int, float)):
                    shots_against_int = shots_against_int if shots_against_int is not None else int(save_shots_raw)
                row["shots_against"] = shots_against_int
                row["saves"] = saves_int
                row["save_pctg"] = p.get("savePctg")
                row["goals_against"] = goals_against
                for f in _GOALIE_FIELDS[3:]:  # skip the three above
                    row[_camel_to_snake(f)] = p.get(f)
                rows.append(row)

    return pd.DataFrame(rows)
