from nhl_bigquery.plays.schema import PLAYS_SCHEMA, get_partitioning


def test_partitioning_is_game_date_day():
    p = get_partitioning()
    assert p.field == "game_date"
    assert p.type == "DAY"
    assert "home_team_abbrev" in p.clustering
    assert "away_team_abbrev" in p.clustering


def test_group_a_columns_present():
    names = {c.name for c in PLAYS_SCHEMA}
    expected = {
        "game_id", "event_id", "sort_order", "season", "game_date", "game_type",
        "period", "period_type", "time_in_period", "time_remaining", "event_abs_seconds",
    }
    missing = expected - names
    assert not missing, f"missing columns: {missing}"


def test_game_id_is_required_int64():
    spec = next(c for c in PLAYS_SCHEMA if c.name == "game_id")
    assert spec.type == "INT64"
    assert spec.mode == "REQUIRED"


def test_game_date_is_required_date():
    spec = next(c for c in PLAYS_SCHEMA if c.name == "game_date")
    assert spec.type == "DATE"
    assert spec.mode == "REQUIRED"


def test_no_duplicate_column_names():
    names = [c.name for c in PLAYS_SCHEMA]
    assert len(names) == len(set(names)), "duplicate column names"


def test_every_column_has_business_definition():
    for spec in PLAYS_SCHEMA:
        assert spec.business_definition.strip(), f"{spec.name} missing business_definition"
