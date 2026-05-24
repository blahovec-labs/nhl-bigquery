"""DIM_PLAYERS_SCHEMA: player dimension (one row per NHL player_id)."""

from __future__ import annotations

from nhl_bigquery.schema import ColumnSpec


def get_partitioning() -> None:
    # Small mutable dimension; no partitioning.
    return None


def _col(name, type, mode, short, defn, *, tags=None, range_=None, values=None,
         example=None, gotchas=None, api_eq=None, api_src=None, dep=None):
    return ColumnSpec(
        name=name, type=type, mode=mode,
        short_description=short, business_definition=defn,
        semantic_tags=list(tags or []),
        valid_range=range_, valid_values=values, example_value=example,
        gotchas=list(gotchas or []),
        nhl_api_equivalent=api_eq, nhl_api_source_field=api_src or name,
        deprecated_in_year=dep,
    )


DIM_PLAYERS_SCHEMA: list[ColumnSpec] = [
    _col("player_id", "INT64", "REQUIRED",
         "NHL player_id (primary key).",
         "Stable integer identifying a single NHL player across seasons. "
         "Canonical join key from nhl_plays role columns and boxscore_stats.",
         tags=["identifier", "join_key"], example=8478402,
         api_eq="playerId", api_src="playerId"),
    _col("first_name", "STRING", "NULLABLE",
         "Player first name.",
         "Default-locale first name as returned by /player/{id}/landing.",
         example="Connor", api_eq="firstName.default", api_src="firstName.default"),
    _col("last_name", "STRING", "NULLABLE",
         "Player last name.",
         "Default-locale last name as returned by /player/{id}/landing.",
         example="McDavid", api_eq="lastName.default", api_src="lastName.default"),
    _col("full_name", "STRING", "NULLABLE",
         "first_name + ' ' + last_name (convenience).",
         "Concatenation of first_name and last_name for display. "
         "Derived client-side, not a raw NHL API field.",
         example="Connor McDavid", api_src="derived"),
    _col("position_code", "STRING", "NULLABLE",
         "Position code (C/L/R/D/G).",
         "Position derived from /player/{id}/landing position field.",
         values=["C", "L", "R", "D", "G"], example="C",
         api_eq="position", api_src="position"),
    _col("sweater_number", "INT64", "NULLABLE",
         "Most recent observed sweater number.",
         "Jersey number on current team. Changes between teams; we keep the latest.",
         range_=(1.0, 99.0), example=97,
         api_eq="sweaterNumber", api_src="sweaterNumber"),
    _col("current_team_abbrev", "STRING", "NULLABLE",
         "Most recent team abbreviation.",
         "Three-letter team abbrev for the player's current team. NULL if free agent.",
         example="EDM", api_eq="currentTeamAbbrev", api_src="currentTeamAbbrev"),
    _col("shoots_catches", "STRING", "NULLABLE",
         "Shoots / catches handedness (L/R).",
         "For skaters this is shoots; for goalies this is catches.",
         values=["L", "R"], example="L",
         api_eq="shootsCatches", api_src="shootsCatches"),
    _col("birth_date", "DATE", "NULLABLE",
         "Player birth date.",
         "ISO date of birth. Stable across the player's career.",
         example="1997-01-13", api_eq="birthDate", api_src="birthDate"),
    _col("birth_country", "STRING", "NULLABLE",
         "Birth country (ISO-3166 alpha-3).",
         "Country of birth as 3-letter ISO code.",
         example="CAN", api_eq="birthCountry", api_src="birthCountry"),
    _col("height_inches", "INT64", "NULLABLE",
         "Height in inches.",
         "Player height in inches as reported by NHL.",
         range_=(60.0, 84.0), example=73,
         api_eq="heightInInches", api_src="heightInInches"),
    _col("weight_pounds", "INT64", "NULLABLE",
         "Weight in pounds.",
         "Player weight in pounds as reported by NHL.",
         range_=(140.0, 280.0), example=193,
         api_eq="weightInPounds", api_src="weightInPounds"),
    _col("headshot_url", "STRING", "NULLABLE",
         "Headshot image URL.",
         "Headshot image URL hosted by NHL.com. May redirect or 404 for retired players.",
         example="https://assets.nhle.com/mugs/nhl/default-skater.png",
         api_eq="headshot", api_src="headshot"),
    _col("ingested_at", "TIMESTAMP", "REQUIRED",
         "When this row was last upserted by nhl-bigquery.",
         "UTC timestamp of the most recent fetch from /player/{id}/landing. "
         "Used by from-plays discovery to skip recently-fetched IDs.",
         tags=["meta"], api_src="(set by ingestion)"),
]
