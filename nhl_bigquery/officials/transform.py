"""Officials transform: /gamecenter/{id}/right-rail → officials rows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd


def _official_name(o: dict[str, Any]) -> str | None:
    # 2026-27 API: {"fullName": {"default": name}}; older: {"default": name}.
    return ((o.get("fullName") or {}).get("default")) or o.get("default")


def _official_number(o: dict[str, Any]) -> str | None:
    # API sends sweaterNumber as an int; the column is STRING.
    n = o.get("sweaterNumber")
    return None if n is None else str(n)


def transform_right_rail_to_officials_df(
    rr: dict[str, Any], *, game_id: int, game_date: str
) -> pd.DataFrame:
    """Extract referees + linesmen into a long-format DataFrame."""
    info = (rr or {}).get("gameInfo") or {}
    rows = []
    ingested_at = datetime.now(UTC)

    for i, ref in enumerate(info.get("referees") or [], start=1):
        rows.append({
            "game_id": game_id,
            "game_date": game_date,
            "role": f"REFEREE_{i}",
            "official_name": _official_name(ref or {}),
            "official_number": _official_number(ref or {}),
            "ingested_at": ingested_at,
        })
    for i, ln in enumerate(info.get("linesmen") or [], start=1):
        rows.append({
            "game_id": game_id,
            "game_date": game_date,
            "role": f"LINESMAN_{i}",
            "official_name": _official_name(ln or {}),
            "official_number": _official_number(ln or {}),
            "ingested_at": ingested_at,
        })
    return pd.DataFrame(rows)
