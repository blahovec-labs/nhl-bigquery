"""Merge play-by-play events with shift-charts to produce on-ice arrays.

Algorithm:
  1. Parse each shift into absolute-seconds intervals (half-open).
  2. For each event with event_abs_seconds = t:
       on_ice_at(t) = {player_id | shift.start <= t < shift.end}
  3. Split by team_id into home_on_ice_ids and away_on_ice_ids.

Edge cases handled:
  - event_abs_seconds=None (shootout) → empty arrays, source_quality unchanged
  - empty shifts list → empty arrays, source_quality='NO_SHIFTS'
  - half-open interval (shift end exactly at event time → player NOT on ice)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nhl_bigquery.time_utils import parse_mmss

PERIOD_LENGTH_SECONDS = 1200


@dataclass(frozen=True)
class OnIceResult:
    home_on_ice_ids: list[int] = field(default_factory=list)
    away_on_ice_ids: list[int] = field(default_factory=list)
    source_quality: str = "FULL"


def parse_shifts(raw_shifts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert raw shift-chart records to dicts with abs_seconds intervals.

    Each record is expected to have:
      playerId, teamId, period, startTime (MM:SS), endTime (MM:SS), shiftNumber.

    Skips rows where any required field is missing or cannot be parsed —
    never raises on malformed input.
    """
    out: list[dict[str, Any]] = []
    for r in raw_shifts:
        try:
            period = int(r.get("period", 0))
            start = parse_mmss(r.get("startTime"))
            end = parse_mmss(r.get("endTime"))
            if start is None or end is None or period < 1:
                continue
            offset = (period - 1) * PERIOD_LENGTH_SECONDS
            out.append({
                "player_id": int(r["playerId"]),
                "team_id": int(r["teamId"]),
                "period": period,
                "shift_number": int(r.get("shiftNumber", 0)),
                "start_abs_seconds": offset + start,
                "end_abs_seconds": offset + end,
            })
        except (KeyError, ValueError, TypeError):
            continue
    return out


def build_on_ice_at_event(
    parsed_shifts: list[dict[str, Any]],
    event_abs_seconds: int | None,
    home_team_id: int,
    away_team_id: int,
) -> OnIceResult:
    """Compute on-ice arrays for a single event.

    Interval semantics: a player is on ice when
        shift.start_abs_seconds <= event_abs_seconds < shift.end_abs_seconds
    (half-open on the right — a player whose shift ends exactly at the event
    time is NOT considered on ice).

    Returns:
      - Empty arrays + source_quality='NO_SHIFTS' when parsed_shifts is empty.
      - Empty arrays + source_quality='FULL' for shootout events
        (event_abs_seconds=None), because shootouts legitimately have no
        on-ice array but shift data is still present.
    """
    if not parsed_shifts:
        return OnIceResult(source_quality="NO_SHIFTS")
    if event_abs_seconds is None:
        return OnIceResult(source_quality="FULL")

    home_ids: list[int] = []
    away_ids: list[int] = []
    for s in parsed_shifts:
        if s["start_abs_seconds"] <= event_abs_seconds < s["end_abs_seconds"]:
            if s["team_id"] == home_team_id:
                home_ids.append(s["player_id"])
            elif s["team_id"] == away_team_id:
                away_ids.append(s["player_id"])
    home_ids.sort()
    away_ids.sort()
    return OnIceResult(
        home_on_ice_ids=home_ids,
        away_on_ice_ids=away_ids,
        source_quality="FULL",
    )
