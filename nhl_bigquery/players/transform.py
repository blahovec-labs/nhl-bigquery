"""Players transform: /player/{id}/landing → DataFrame row."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd


def transform_player_landing_to_row(landing: dict[str, Any]) -> dict[str, Any]:
    """Convert one /player/{id}/landing response to a dim_players row dict."""
    first = (landing.get("firstName") or {}).get("default")
    last = (landing.get("lastName") or {}).get("default")
    full = " ".join(p for p in [first, last] if p) or None
    return {
        "player_id": int(landing["playerId"]),
        "first_name": first,
        "last_name": last,
        "full_name": full,
        "position_code": landing.get("position"),
        "sweater_number": landing.get("sweaterNumber"),
        "current_team_abbrev": landing.get("currentTeamAbbrev"),
        "shoots_catches": landing.get("shootsCatches"),
        "birth_date": landing.get("birthDate"),
        "birth_country": landing.get("birthCountry"),
        "height_inches": landing.get("heightInInches"),
        "weight_pounds": landing.get("weightInPounds"),
        "headshot_url": landing.get("headshot"),
        "ingested_at": datetime.now(UTC),
    }


def transform_player_landings_to_df(landings: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert a batch of landing responses to a dim_players DataFrame."""
    return pd.DataFrame([transform_player_landing_to_row(L) for L in landings])
