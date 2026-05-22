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


def test_group_b_columns_present():
    names = {c.name for c in PLAYS_SCHEMA}
    expected = {
        "event_type", "event_type_desc", "situation_code",
        "x_coord", "y_coord", "zone_code", "zone_descriptor",
    }
    missing = expected - names
    assert not missing, f"missing columns: {missing}"


def test_event_type_has_valid_values():
    spec = next(c for c in PLAYS_SCHEMA if c.name == "event_type")
    assert spec.valid_values is not None
    assert "GOAL" in spec.valid_values
    assert "FACEOFF" in spec.valid_values
    assert "SHOT" in spec.valid_values


def test_coords_have_valid_range():
    x = next(c for c in PLAYS_SCHEMA if c.name == "x_coord")
    y = next(c for c in PLAYS_SCHEMA if c.name == "y_coord")
    assert x.valid_range == (-100.0, 100.0)
    assert y.valid_range == (-42.5, 42.5)


def test_group_c_player_columns_present():
    names = {c.name for c in PLAYS_SCHEMA}
    expected = {
        "event_owner_team_id",
        "shooter_id", "goalie_id", "scorer_id",
        "primary_assist_id", "secondary_assist_id",
        "hitter_id", "hittee_id",
        "winning_player_id", "losing_player_id",
        "drawn_by_id", "served_by_id",
        "penalty_player_id", "blocker_id", "committed_by_id",
    }
    missing = expected - names
    assert not missing, f"missing columns: {missing}"


def test_player_role_columns_are_nullable_int64():
    role_cols = {
        "shooter_id", "goalie_id", "scorer_id",
        "primary_assist_id", "secondary_assist_id",
        "hitter_id", "hittee_id",
        "winning_player_id", "losing_player_id",
        "drawn_by_id", "served_by_id",
        "penalty_player_id", "blocker_id", "committed_by_id",
    }
    for spec in PLAYS_SCHEMA:
        if spec.name in role_cols:
            assert spec.type == "INT64", f"{spec.name}: type"
            assert spec.mode == "NULLABLE", f"{spec.name}: mode"


def test_group_d_columns_present():
    names = {c.name for c in PLAYS_SCHEMA}
    expected = {
        "shot_type",
        "penalty_minutes", "penalty_severity", "penalty_type_code", "penalty_type_desc",
        "home_score_before", "away_score_before",
        "home_score_after", "away_score_after",
        "home_team_id", "away_team_id", "home_team_abbrev", "away_team_abbrev",
    }
    missing = expected - names
    assert not missing, f"missing columns: {missing}"


def test_penalty_severity_has_valid_values():
    spec = next(c for c in PLAYS_SCHEMA if c.name == "penalty_severity")
    assert "MIN" in (spec.valid_values or [])
    assert "MAJ" in (spec.valid_values or [])


def test_group_e_columns_present():
    names = {c.name for c in PLAYS_SCHEMA}
    expected = {
        "home_on_ice_ids", "away_on_ice_ids",
        "home_skaters_on_ice", "away_skaters_on_ice",
        "home_goalie_on_ice", "away_goalie_on_ice",
        "strength_state",
        "source_quality", "ingested_at",
    }
    missing = expected - names
    assert not missing, f"missing columns: {missing}"


def test_on_ice_arrays_are_repeated_int64():
    for name in ("home_on_ice_ids", "away_on_ice_ids"):
        spec = next(c for c in PLAYS_SCHEMA if c.name == name)
        assert spec.type == "INT64", f"{name} type"
        assert spec.mode == "REPEATED", f"{name} mode"


def test_strength_state_has_valid_values():
    spec = next(c for c in PLAYS_SCHEMA if c.name == "strength_state")
    assert "EV" in (spec.valid_values or [])
    assert "PP_H" in (spec.valid_values or [])
    assert "3v3" in (spec.valid_values or [])


def test_full_plays_schema_has_no_duplicate_names():
    names = [c.name for c in PLAYS_SCHEMA]
    assert len(names) == len(set(names))
