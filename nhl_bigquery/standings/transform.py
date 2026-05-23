"""Standings transform: /standings/{date} → daily-snapshot rows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd


def transform_standings_to_df(
    st: dict[str, Any], *, snapshot_date: str
) -> pd.DataFrame:
    """Convert /standings/{date} response to a per-team snapshot DataFrame."""
    ingested_at = datetime.now(UTC)
    rows = []
    for s in (st or {}).get("standings") or []:
        team_abbrev = (s.get("teamAbbrev") or {}).get("default")
        team_id = (s.get("teamAbbrev") or {}).get("id") or (s.get("teamCommonName") or {}).get("id")
        rows.append({
            "snapshot_date": snapshot_date,
            "team_id": int(team_id) if team_id is not None else None,
            "team_abbrev": team_abbrev,
            "team_name": (s.get("teamName") or {}).get("default"),
            "conference_name": s.get("conferenceName"),
            "division_name": s.get("divisionName"),
            "games_played": s.get("gamesPlayed"),
            "wins": s.get("wins"),
            "losses": s.get("losses"),
            "ot_losses": s.get("otLosses"),
            "points": s.get("points"),
            "goal_for": s.get("goalFor"),
            "goal_against": s.get("goalAgainst"),
            "goal_differential": s.get("goalDifferential"),
            "regulation_wins": s.get("regulationWins"),
            "regulation_plus_ot_wins": s.get("regulationPlusOtWins"),
            "ingested_at": ingested_at,
        })
    return pd.DataFrame(rows)
