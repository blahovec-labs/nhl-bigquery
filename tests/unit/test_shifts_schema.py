from nhl_bigquery.shifts.schema import SHIFTS_SCHEMA, get_partitioning


def test_partitioning():
    p = get_partitioning()
    assert p.field == "game_date"
    assert p.clustering == ["player_id"]


def test_required_columns_present():
    names = {c.name for c in SHIFTS_SCHEMA}
    expected = {"game_id", "game_date", "player_id", "team_id",
                "shift_number", "period", "period_type",
                "start_in_period", "end_in_period",
                "start_abs_seconds", "end_abs_seconds", "duration_seconds",
                "ingested_at"}
    assert expected.issubset(names), f"missing: {expected - names}"
