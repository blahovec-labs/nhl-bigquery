"""DIM_PLAYERS_SCHEMA invariants and shape."""

from nhl_bigquery.players.schema import DIM_PLAYERS_SCHEMA, get_partitioning


def test_schema_has_expected_columns():
    names = {c.name for c in DIM_PLAYERS_SCHEMA}
    assert names == {
        "player_id", "first_name", "last_name", "full_name",
        "position_code", "sweater_number", "current_team_abbrev",
        "shoots_catches", "birth_date", "birth_country",
        "height_inches", "weight_pounds", "headshot_url", "ingested_at",
    }


def test_player_id_is_required_primary_key():
    pid = next(c for c in DIM_PLAYERS_SCHEMA if c.name == "player_id")
    assert pid.type == "INT64"
    assert pid.mode == "REQUIRED"


def test_position_code_has_valid_values_constraint():
    pc = next(c for c in DIM_PLAYERS_SCHEMA if c.name == "position_code")
    assert pc.valid_values == ["C", "L", "R", "D", "G"]


def test_ingested_at_is_timestamp_required():
    ts = next(c for c in DIM_PLAYERS_SCHEMA if c.name == "ingested_at")
    assert ts.type == "TIMESTAMP"
    assert ts.mode == "REQUIRED"


def test_partitioning_returns_none():
    # dim_players is a small mutable dimension — no partitioning.
    assert get_partitioning() is None
