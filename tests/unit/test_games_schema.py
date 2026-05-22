# tests/unit/test_games_schema.py
from nhl_bigquery.games.schema import GAMES_SCHEMA, get_partitioning


def test_partitioning():
    p = get_partitioning()
    assert p.field == "game_date"
    assert p.clustering == ["season", "game_type"]


def test_required_columns_present():
    names = {c.name for c in GAMES_SCHEMA}
    required = {
        "game_id", "game_date", "season", "game_type",
        "home_team_id", "away_team_id", "home_team_abbrev", "away_team_abbrev",
        "venue_default_name", "start_time_utc", "game_state",
        "final_period_type", "home_score_final", "away_score_final",
        "is_shootout_decided", "ingested_at",
    }
    assert required.issubset(names), f"missing: {required - names}"


def test_game_id_required():
    spec = next(c for c in GAMES_SCHEMA if c.name == "game_id")
    assert spec.mode == "REQUIRED"


def test_no_duplicates():
    names = [c.name for c in GAMES_SCHEMA]
    assert len(names) == len(set(names))
