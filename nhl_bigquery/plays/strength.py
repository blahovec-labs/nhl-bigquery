"""Derive strength_state from on-ice skater counts + goalie flags.

Canonical labels (one per distinguishable on-ice state):
  EV   = 5v5 with both goalies in
  PP_H = home power play (more home skaters than away skaters)
  PP_A = away power play (more away skaters than home skaters)
  EN_H = home goalie pulled
  EN_A = away goalie pulled
  4v4  = even skater count, 4 each
  3v3  = even skater count, 3 each (regular-season OT)

SH_H / SH_A are NOT used here because they describe the same state as
PP_A / PP_H respectively — one canonical label per state simplifies
downstream filters.
"""

from __future__ import annotations


def derive_strength_state(
    home_skaters: int,
    away_skaters: int,
    home_goalie: bool,
    away_goalie: bool,
) -> str | None:
    """Return canonical strength_state string, or None if state is invalid."""
    if home_skaters < 1 or away_skaters < 1:
        return None

    # Empty-net cases take precedence — a pulled goalie defines the state
    if not home_goalie and away_goalie:
        return "EN_H"
    if not away_goalie and home_goalie:
        return "EN_A"

    # Even skater counts → label by absolute count
    if home_skaters == away_skaters:
        if home_skaters == 5:
            return "EV"
        if home_skaters == 4:
            return "4v4"
        if home_skaters == 3:
            return "3v3"
        return f"{home_skaters}v{away_skaters}"

    # Unequal skater counts → power play label
    if home_skaters > away_skaters:
        return "PP_H"
    return "PP_A"
