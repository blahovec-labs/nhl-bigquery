"""STANDINGS_SCHEMA: daily team standings snapshot."""

from __future__ import annotations

from nhl_bigquery.games.schema import _col
from nhl_bigquery.schema import ColumnSpec, PartitioningSpec


def get_partitioning() -> PartitioningSpec:
    return PartitioningSpec(
        field="snapshot_date", type="DAY",
        clustering=["conference_name", "division_name"],
    )


STANDINGS_SCHEMA: list[ColumnSpec] = [
    _col("snapshot_date", "DATE", "REQUIRED", "Snapshot calendar date.",
         "Date the standings were captured (sourced from /standings/{date}).",
         tags=["temporal", "identifier"], example="2024-10-08",
         api_eq=None, api_src="(date passed to /standings/{date})"),
    _col("team_id", "INT64", "REQUIRED", "Team ID.",
         "NHL team_id.", tags=["identifier", "join_key", "team"], example=10,
         api_eq="teamCommonName.id (or teamAbbrev.id)", api_src="teamAbbrev.id"),
    _col("team_abbrev", "STRING", "NULLABLE", "Team 3-letter abbreviation.",
         "Three-letter team abbreviation.", tags=["team"], example="TOR",
         api_eq="teamAbbrev.default", api_src="teamAbbrev.default"),
    _col("team_name", "STRING", "NULLABLE", "Team display name.",
         "Full team name (English).", tags=["team"], example="Toronto Maple Leafs",
         api_eq="teamName.default", api_src="teamName.default"),
    _col("conference_name", "STRING", "NULLABLE", "Conference.",
         "Eastern or Western.", tags=["team"], example="Eastern",
         api_eq="conferenceName", api_src="conferenceName"),
    _col("division_name", "STRING", "NULLABLE", "Division.",
         "Atlantic / Metropolitan / Central / Pacific.",
         tags=["team"], example="Atlantic",
         api_eq="divisionName", api_src="divisionName"),
    _col("games_played", "INT64", "NULLABLE", "Games played.",
         "Total games played in the season as of snapshot_date.",
         tags=["measure"], range_=(0.0, 100.0), example=5,
         api_eq="gamesPlayed", api_src="gamesPlayed"),
    _col("wins", "INT64", "NULLABLE", "Wins.",
         "Wins in the season as of snapshot_date.",
         tags=["measure"], example=3, api_eq="wins", api_src="wins"),
    _col("losses", "INT64", "NULLABLE", "Regulation losses.",
         "Regulation losses (do not include OT/SO losses).",
         tags=["measure"], example=1, api_eq="losses", api_src="losses"),
    _col("ot_losses", "INT64", "NULLABLE", "OT/SO losses.",
         "Losses in overtime or shootout (1 point earned).",
         tags=["measure"], example=1, api_eq="otLosses", api_src="otLosses"),
    _col("points", "INT64", "NULLABLE", "League standings points.",
         "Standings points: 2 for a win, 1 for OT/SO loss, 0 for regulation loss.",
         tags=["measure"], example=7, api_eq="points", api_src="points"),
    _col("goal_for", "INT64", "NULLABLE", "Goals for.",
         "Goals scored by this team in the season.",
         tags=["measure"], example=18, api_eq="goalFor", api_src="goalFor"),
    _col("goal_against", "INT64", "NULLABLE", "Goals against.",
         "Goals allowed by this team in the season.",
         tags=["measure"], example=12, api_eq="goalAgainst", api_src="goalAgainst"),
    _col("goal_differential", "INT64", "NULLABLE", "Goal differential.",
         "goal_for - goal_against.",
         tags=["measure"], example=6, api_eq="goalDifferential",
         api_src="goalDifferential"),
    _col("regulation_wins", "INT64", "NULLABLE", "Regulation wins.",
         "Wins in regulation only (used for tiebreakers).",
         tags=["measure"], example=2, api_eq="regulationWins",
         api_src="regulationWins"),
    _col("regulation_plus_ot_wins", "INT64", "NULLABLE", "REG+OT wins.",
         "Wins in regulation or overtime (excludes shootout wins). Used for tiebreakers.",
         tags=["measure"], example=3, api_eq="regulationPlusOtWins",
         api_src="regulationPlusOtWins"),
    _col("ingested_at", "TIMESTAMP", "REQUIRED",
         "Ingestion timestamp.",
         "UTC timestamp when this row was written.",
         tags=["meta"], example="2026-05-22T17:00:00Z",
         api_eq=None, api_src="(set by ingestion)"),
]
