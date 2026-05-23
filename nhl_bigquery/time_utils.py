"""Time parsing for NHL play-by-play and shift-charts.

NHL times come as "M:SS" or "MM:SS" within a period. Period offsets
are always 1200 seconds (20 min) in absolute time, even for regular-
season 3v3 OT (which only lasts up to 300s — timeInPeriod never
exceeds 300 there, so the offset math is consistent).
"""

from __future__ import annotations

PERIOD_LENGTH_SECONDS = 1200


def parse_mmss(value: str | None) -> int | None:
    """Convert "M:SS" or "MM:SS" to seconds. Returns None for None input.

    Raises ValueError on malformed strings or out-of-range seconds (>= 60).
    """
    if value is None:
        return None
    s = value.strip()
    if not s:
        raise ValueError("empty time string")
    parts = s.split(":")
    if len(parts) != 2:
        raise ValueError(f"expected MM:SS, got {value!r}")
    minutes_str, seconds_str = parts
    minutes = int(minutes_str)
    seconds = int(seconds_str)
    if seconds < 0 or seconds >= 60:
        raise ValueError(f"seconds out of range in {value!r}")
    if minutes < 0:
        raise ValueError(f"negative minutes in {value!r}")
    return minutes * 60 + seconds


def event_abs_seconds(period: int, time_in_period: str | None) -> int | None:
    """Compute absolute seconds from game start.

    Returns None for shootout (period_type='SO') events whose time_in_period is None.
    """
    parsed = parse_mmss(time_in_period)
    if parsed is None:
        return None
    return (period - 1) * PERIOD_LENGTH_SECONDS + parsed
