"""Inventory of tables + their schemas for the renderers to walk."""

from __future__ import annotations

from nhl_bigquery.boxscore.schema import BOXSCORE_SCHEMA
from nhl_bigquery.boxscore.schema import get_partitioning as boxscore_part
from nhl_bigquery.games.schema import GAMES_SCHEMA
from nhl_bigquery.games.schema import get_partitioning as games_part
from nhl_bigquery.officials.schema import OFFICIALS_SCHEMA
from nhl_bigquery.officials.schema import get_partitioning as officials_part
from nhl_bigquery.plays.schema import PLAYS_SCHEMA
from nhl_bigquery.plays.schema import get_partitioning as plays_part
from nhl_bigquery.shifts.schema import SHIFTS_SCHEMA
from nhl_bigquery.shifts.schema import get_partitioning as shifts_part
from nhl_bigquery.standings.schema import STANDINGS_SCHEMA
from nhl_bigquery.standings.schema import get_partitioning as standings_part

TABLES: dict[str, dict] = {
    "nhl_plays":     {"schema": PLAYS_SCHEMA,     "partitioning": plays_part()},
    "games":         {"schema": GAMES_SCHEMA,     "partitioning": games_part()},
    "game_officials":{"schema": OFFICIALS_SCHEMA, "partitioning": officials_part()},
    "boxscore_stats":{"schema": BOXSCORE_SCHEMA,  "partitioning": boxscore_part()},
    "shifts":        {"schema": SHIFTS_SCHEMA,    "partitioning": shifts_part()},
    "standings":     {"schema": STANDINGS_SCHEMA, "partitioning": standings_part()},
}

# Aliases so callers can use short names (e.g. "plays") in addition to the
# canonical BQ table names used as TABLES keys.
_ALIASES: dict[str, str] = {
    "plays": "nhl_plays",
    "officials": "game_officials",
    "boxscore": "boxscore_stats",
}


def resolve_table_kind(table_kind: str) -> str:
    """Return the canonical TABLES key for *table_kind*, resolving aliases."""
    if table_kind in TABLES:
        return table_kind
    resolved = _ALIASES.get(table_kind)
    if resolved is None:
        raise KeyError(
            f"Unknown table_kind {table_kind!r}. "
            f"Valid keys: {list(TABLES)} + aliases {list(_ALIASES)}"
        )
    return resolved
