"""SHIFTS_SCHEMA: per-shift per-player intervals."""

from __future__ import annotations

from nhl_bigquery.games.schema import _col
from nhl_bigquery.schema import ColumnSpec, PartitioningSpec


def get_partitioning() -> PartitioningSpec:
    return PartitioningSpec(
        field="game_date", type="DAY", clustering=["player_id"],
    )


SHIFTS_SCHEMA: list[ColumnSpec] = [
    _col("game_id", "INT64", "REQUIRED", "NHL game ID.",
         "FK to games.game_id.", tags=["identifier", "join_key"], example=2024020001,
         api_eq="gameId", api_src="gameId"),
    _col("game_date", "DATE", "REQUIRED", "Game date.",
         "Partition key.", tags=["temporal"], example="2024-10-08",
         api_eq=None, api_src="(joined from games)"),
    _col("player_id", "INT64", "REQUIRED", "NHL Player ID.",
         "Player who took this shift.", tags=["identifier", "join_key"],
         example=8478402, api_eq="playerId", api_src="playerId"),
    _col("team_id", "INT64", "REQUIRED", "Team ID.",
         "Team the player suited up for in this game.",
         tags=["identifier", "join_key", "team"], example=10,
         api_eq="teamId", api_src="teamId"),
    _col("shift_number", "INT64", "REQUIRED", "Shift index (1-based per game per player).",
         "Sequential shift counter for a player in a game.",
         tags=["identifier"], range_=(1.0, 50.0), example=3,
         api_eq="shiftNumber", api_src="shiftNumber"),
    _col("period", "INT64", "NULLABLE", "Period (1-N).",
         "Period in which the shift began.", tags=["temporal"],
         range_=(1.0, 10.0), example=1,
         api_eq="period", api_src="period"),
    _col("period_type", "STRING", "NULLABLE", "Period type.",
         "REG / OT / SO.", tags=["temporal"], values=["REG", "OT", "SO"], example="REG",
         api_eq=None, api_src="(derived from period)"),
    _col("start_in_period", "STRING", "NULLABLE", "Shift start (MM:SS in period).",
         "Time within the period when the shift started.",
         tags=["temporal"], example="2:14",
         api_eq="startTime", api_src="startTime"),
    _col("end_in_period", "STRING", "NULLABLE", "Shift end (MM:SS in period).",
         "Time within the period when the shift ended.",
         tags=["temporal"], example="2:48",
         api_eq="endTime", api_src="endTime"),
    _col("start_abs_seconds", "INT64", "NULLABLE", "Shift start (absolute seconds).",
         "Derived: (period-1)*1200 + parse_mmss(start_in_period). Use for time-based joins.",
         tags=["temporal", "derived"], range_=(0.0, 12000.0), example=134,
         api_eq=None, api_src="(derived)"),
    _col("end_abs_seconds", "INT64", "NULLABLE", "Shift end (absolute seconds).",
         "Derived end time in absolute seconds. Half-open interval: a player on shift "
         "from start_abs_seconds (inclusive) to end_abs_seconds (exclusive).",
         tags=["temporal", "derived"], range_=(0.0, 12000.0), example=168,
         api_eq=None, api_src="(derived)"),
    _col("duration_seconds", "INT64", "NULLABLE", "Shift duration (s).",
         "end_abs_seconds - start_abs_seconds.",
         tags=["temporal", "derived"], range_=(1.0, 600.0), example=34,
         api_eq=None, api_src="(derived)"),
    _col("ingested_at", "TIMESTAMP", "REQUIRED",
         "Ingestion timestamp.",
         "UTC timestamp when this row was written.",
         tags=["meta"], example="2026-05-22T17:00:00Z",
         api_eq=None, api_src="(set by ingestion)"),
]
