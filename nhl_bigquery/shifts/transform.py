"""Shifts transform: /gamecenter/{id}/shift-charts → per-shift rows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from nhl_bigquery.time_utils import parse_mmss


def transform_shift_charts_to_df(
    sc: dict[str, Any], *, game_date: str
) -> pd.DataFrame:
    """Convert shift-charts response to a per-shift DataFrame."""
    ingested_at = datetime.now(timezone.utc)
    rows = []
    for s in (sc or {}).get("data") or []:
        try:
            period = int(s.get("period"))
            start_s = parse_mmss(s.get("startTime"))
            end_s = parse_mmss(s.get("endTime"))
        except (ValueError, TypeError):
            continue
        if start_s is None or end_s is None or end_s <= start_s:
            continue
        offset = (period - 1) * 1200
        rows.append({
            "game_id": int(s["gameId"]),
            "game_date": game_date,
            "player_id": int(s["playerId"]),
            "team_id": int(s["teamId"]),
            "shift_number": int(s.get("shiftNumber") or 0),
            "period": period,
            "period_type": "OT" if period >= 4 else "REG",
            "start_in_period": s.get("startTime"),
            "end_in_period": s.get("endTime"),
            "start_abs_seconds": offset + start_s,
            "end_abs_seconds": offset + end_s,
            "duration_seconds": end_s - start_s,
            "ingested_at": ingested_at,
        })
    return pd.DataFrame(rows)
