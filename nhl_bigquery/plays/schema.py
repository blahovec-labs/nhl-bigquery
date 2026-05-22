"""PLAYS_SCHEMA: single source of truth for the nhl_plays table.

This file is built up in groups (identifiers, time, event classification,
coords, players, shot details, penalty details, on-ice state, score state,
team context, source-quality). Authored across multiple tasks to keep
each commit reviewable.
"""

from __future__ import annotations

from nhl_bigquery.schema import ColumnSpec, PartitioningSpec


def get_partitioning() -> PartitioningSpec:
    return PartitioningSpec(
        field="game_date",
        type="DAY",
        clustering=["home_team_abbrev", "away_team_abbrev", "game_id"],
    )


PLAYS_SCHEMA: list[ColumnSpec] = [
    # -------------------------------------------------------------------------
    # Group A: Identifiers + time/period
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="game_id",
        type="INT64",
        mode="REQUIRED",
        short_description="NHL unique game identifier.",
        business_definition=(
            "Stable integer identifying a single NHL game across all data sources. "
            "Use as the canonical join key to games, boxscore_stats, shifts, and "
            "game_officials. Format: <season-year><game-type:02-04><sequence>."
        ),
        semantic_tags=["identifier", "join_key", "nhl_canonical"],
        valid_range=None, valid_values=None, example_value=2024020001,
        gotchas=[
            "game_type digit: 01=preseason, 02=regular, 03=playoffs, 04=all-star.",
        ],
        nhl_api_equivalent="id",
        nhl_api_source_field="id",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="event_id",
        type="INT64",
        mode="REQUIRED",
        short_description="NHL event ID within a game.",
        business_definition=(
            "Per-game sequential event identifier from the play-by-play API. Unique "
            "within (game_id, event_id). Use sort_order for stable ordering of plays "
            "in display contexts."
        ),
        semantic_tags=["identifier", "join_key"],
        valid_range=None, valid_values=None, example_value=12,
        gotchas=[
            "event_id is unique per game, NOT globally — always join with game_id.",
        ],
        nhl_api_equivalent="eventId",
        nhl_api_source_field="eventId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="sort_order",
        type="INT64",
        mode="NULLABLE",
        short_description="Stable display ordering of events within a game.",
        business_definition=(
            "Sequential integer (1..N) assigned during ingestion that reflects the "
            "intended display ordering of plays within a game. Use this instead of "
            "event_id for ordering — event_id can have gaps."
        ),
        semantic_tags=["ordering"],
        valid_range=(1.0, 2000.0), valid_values=None, example_value=42,
        gotchas=[],
        nhl_api_equivalent="sortOrder",
        nhl_api_source_field="sortOrder",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="season",
        type="INT64",
        mode="REQUIRED",
        short_description="Season start year (e.g., 2024 for 2024-25).",
        business_definition=(
            "Four-digit year denoting the season starting year. The 2024-25 NHL "
            "season is season=2024. Useful for season-grain filters and joins."
        ),
        semantic_tags=["temporal", "identifier"],
        valid_range=(2010.0, 2050.0), valid_values=None, example_value=2024,
        gotchas=[
            "Always the START year — playoff games in May 2025 still have season=2024.",
        ],
        nhl_api_equivalent="season (first 4 digits, e.g. 20242025 → 2024)",
        nhl_api_source_field="season",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="game_date",
        type="DATE",
        mode="REQUIRED",
        short_description="Calendar date the game was played (local venue).",
        business_definition=(
            "Date the game was played, sourced from gameDate. Serves as the BigQuery "
            "partition key for this table."
        ),
        semantic_tags=["temporal", "identifier"],
        valid_range=None, valid_values=None, example_value="2024-10-08",
        gotchas=[],
        nhl_api_equivalent="gameDate",
        nhl_api_source_field="gameDate",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="game_type",
        type="STRING",
        mode="NULLABLE",
        short_description="Game type code (PR/R/P/AS).",
        business_definition=(
            "Game type derived from the game_id type digit. PR=preseason, R=regular, "
            "P=playoffs, AS=all-star. Most analyses should filter game_type='R' for "
            "regular-season rate stats."
        ),
        semantic_tags=["identifier"],
        valid_range=None, valid_values=["PR", "R", "P", "AS"], example_value="R",
        gotchas=[],
        nhl_api_equivalent="gameType (numeric → coded)",
        nhl_api_source_field="gameType",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="period",
        type="INT64",
        mode="NULLABLE",
        short_description="Period number (1-3 regulation, 4+ OT, 5 SO).",
        business_definition=(
            "Period number when the event occurred. 1-3 are regulation, 4 is "
            "regular-season OT (3v3, 5 min) or playoff OT (5v5, continuous "
            "20-min periods), and 5 is the shootout (regular season only)."
        ),
        semantic_tags=["temporal", "pitch_context"],
        valid_range=(1.0, 10.0), valid_values=None, example_value=2,
        gotchas=[
            "Playoff games can have period > 4 for multi-OT thrillers.",
        ],
        nhl_api_equivalent="periodDescriptor.number",
        nhl_api_source_field="periodDescriptor.number",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="period_type",
        type="STRING",
        mode="NULLABLE",
        short_description="Period type: REG, OT, SO.",
        business_definition=(
            "Type of period the event occurred in. REG=regulation, OT=overtime, "
            "SO=shootout. Use this to filter shootout events out of skater stats."
        ),
        semantic_tags=["temporal", "pitch_context"],
        valid_range=None, valid_values=["REG", "OT", "SO"], example_value="REG",
        gotchas=[
            "Shootout (SO) events have NULL time_in_period and event_abs_seconds.",
        ],
        nhl_api_equivalent="periodDescriptor.periodType",
        nhl_api_source_field="periodDescriptor.periodType",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="time_in_period",
        type="STRING",
        mode="NULLABLE",
        short_description="MM:SS elapsed in the current period.",
        business_definition=(
            "Elapsed time within the current period as MM:SS. 0:00 means the start "
            "of the period. NULL for shootout events."
        ),
        semantic_tags=["temporal"],
        valid_range=None, valid_values=None, example_value="14:32",
        gotchas=[
            "String, not duration — use event_abs_seconds for arithmetic.",
        ],
        nhl_api_equivalent="timeInPeriod",
        nhl_api_source_field="timeInPeriod",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="time_remaining",
        type="STRING",
        mode="NULLABLE",
        short_description="MM:SS remaining in the current period.",
        business_definition=(
            "Time remaining in the current period as MM:SS. The complement of "
            "time_in_period (sums to 20:00 in regulation, 5:00 in regular-season OT)."
        ),
        semantic_tags=["temporal"],
        valid_range=None, valid_values=None, example_value="5:28",
        gotchas=[],
        nhl_api_equivalent="timeRemaining",
        nhl_api_source_field="timeRemaining",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="event_abs_seconds",
        type="INT64",
        mode="NULLABLE",
        short_description="Derived: absolute seconds from game start.",
        business_definition=(
            "Derived during ingestion: (period - 1) * 1200 + parse_mmss(time_in_period). "
            "NULL for shootout events. Use this for time-based joins (shifts) and "
            "windowed aggregations within a game."
        ),
        semantic_tags=["temporal", "derived"],
        valid_range=(0.0, 12000.0), valid_values=None, example_value=872,
        gotchas=[
            "Derived field, not from the NHL API. NULL for shootout events.",
        ],
        nhl_api_equivalent=None,
        nhl_api_source_field="(derived from periodDescriptor.number + timeInPeriod)",
        deprecated_in_year=None,
    ),
]
