"""Officials transform: /gamecenter/{id}/right-rail → officials rows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


def transform_right_rail_to_officials_df(
    rr: dict[str, Any], *, game_id: int, game_date: str
) -> pd.DataFrame:
    """Extract referees + linesmen into a long-format DataFrame."""
    info = (rr or {}).get("gameInfo") or {}
    rows = []
    ingested_at = datetime.now(timezone.utc)

    for i, ref in enumerate(info.get("referees") or [], start=1):
        rows.append({
            "game_id": game_id,
            "game_date": game_date,
            "role": f"REFEREE_{i}",
            "official_name": (ref or {}).get("default"),
            "official_number": (ref or {}).get("sweaterNumber"),
            "ingested_at": ingested_at,
        })
    for i, ln in enumerate(info.get("linesmen") or [], start=1):
        rows.append({
            "game_id": game_id,
            "game_date": game_date,
            "role": f"LINESMAN_{i}",
            "official_name": (ln or {}).get("default"),
            "official_number": (ln or {}).get("sweaterNumber"),
            "ingested_at": ingested_at,
        })
    return pd.DataFrame(rows)
