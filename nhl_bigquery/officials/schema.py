"""OFFICIALS_SCHEMA: one row per official-role pair per game."""

from __future__ import annotations

from nhl_bigquery.games.schema import _col
from nhl_bigquery.schema import PartitioningSpec


def get_partitioning() -> PartitioningSpec:
    return PartitioningSpec(
        field="game_date", type="DAY", clustering=["game_id"],
    )


OFFICIALS_SCHEMA: list = [
    _col("game_id", "INT64", "REQUIRED",
         "NHL unique game identifier.",
         "Stable integer identifying a single NHL game. Join key to nhl_games / nhl_plays.",
         tags=["identifier", "join_key"], example=2024020001,
         api_eq="id", api_src="id"),
    _col("game_date", "DATE", "REQUIRED",
         "Date the game was played.",
         "Calendar date of the game. Partition key for this table.",
         tags=["temporal", "identifier"], example="2024-10-08",
         api_eq="gameDate", api_src="gameDate"),
    _col("role", "STRING", "REQUIRED",
         "Official role in this game.",
         "Designates which officiating position this official held: REFEREE_1, REFEREE_2, LINESMAN_1, or LINESMAN_2.",
         tags=["identifier"], values=["REFEREE_1", "REFEREE_2", "LINESMAN_1", "LINESMAN_2"],
         example="REFEREE_1",
         api_eq="officials[].position", api_src="officials[].position"),
    _col("official_name", "STRING", "REQUIRED",
         "Official's full name.",
         "Full name of the official as returned by the NHL API.",
         tags=["person"], example="Tom Chmielewski",
         api_eq="officials[].default", api_src="officials[].default"),
    _col("official_number", "STRING", "NULLABLE",
         "Official's jersey number.",
         "Jersey number worn by the official, stored as a string to preserve leading zeros if any.",
         tags=["identifier"], example="14",
         api_eq="officials[].sweaterNumber", api_src="officials[].sweaterNumber"),
    _col("ingested_at", "TIMESTAMP", "REQUIRED",
         "Ingestion timestamp.",
         "UTC timestamp when this row was written by nhl-bigquery sync.",
         tags=["meta"], example="2026-05-22T17:00:00Z",
         api_eq=None, api_src="(set by ingestion)"),
]
