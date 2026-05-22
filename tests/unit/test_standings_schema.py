from nhl_bigquery.standings.schema import STANDINGS_SCHEMA, get_partitioning


def test_partitioning():
    p = get_partitioning()
    assert p.field == "snapshot_date"
    assert "conference_name" in p.clustering


def test_required_columns_present():
    names = {c.name for c in STANDINGS_SCHEMA}
    expected = {"snapshot_date", "team_id", "team_abbrev", "team_name",
                "conference_name", "division_name",
                "games_played", "wins", "losses", "ot_losses", "points",
                "goal_for", "goal_against", "goal_differential",
                "regulation_wins", "regulation_plus_ot_wins", "ingested_at"}
    assert expected.issubset(names), f"missing: {expected - names}"
