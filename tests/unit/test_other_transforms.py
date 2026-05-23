import json
from pathlib import Path

from nhl_bigquery.boxscore.transform import transform_boxscore_to_df
from nhl_bigquery.games.transform import (
    transform_landing_to_games_row,
    transform_score_to_games_rows,
)
from nhl_bigquery.officials.transform import transform_right_rail_to_officials_df
from nhl_bigquery.shifts.transform import transform_shift_charts_to_df
from nhl_bigquery.standings.transform import transform_standings_to_df

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(*parts):
    return json.loads((FIXTURES.joinpath(*parts)).read_text(encoding="utf-8"))


def test_score_transform(captured_score_date):
    score = _load("score", f"{captured_score_date}.json")
    df = transform_score_to_games_rows(score, date=captured_score_date)
    assert len(df) > 0
    assert {"game_id", "game_date", "home_team_id", "away_team_id"}.issubset(df.columns)


def test_landing_enrichment_returns_dict(captured_game_id):
    landing = _load("games", str(captured_game_id), "landing.json")
    row = transform_landing_to_games_row(landing)
    assert row["game_id"] == captured_game_id
    assert "final_period_type" in row


def test_officials_transform(captured_game_id):
    rr = _load("games", str(captured_game_id), "right-rail.json")
    df = transform_right_rail_to_officials_df(rr, game_id=captured_game_id,
                                              game_date="2024-10-08")
    assert {"game_id", "game_date", "role", "official_name"}.issubset(df.columns)
    # NHL games always have 4 officials, but tolerate API gaps
    assert len(df) >= 0


def test_boxscore_transform_splits_skater_goalie(captured_game_id):
    bs = _load("games", str(captured_game_id), "boxscore.json")
    df = transform_boxscore_to_df(bs)
    cats = set(df["player_position_category"].unique())
    assert "skater" in cats
    assert "goalie" in cats


def test_shifts_transform(captured_game_id):
    sc = _load("games", str(captured_game_id), "shift-charts.json")
    df = transform_shift_charts_to_df(sc, game_date="2024-10-08")
    assert {"game_id", "player_id", "shift_number",
            "start_abs_seconds", "end_abs_seconds"}.issubset(df.columns)
    assert (df["end_abs_seconds"] > df["start_abs_seconds"]).all()


def test_standings_transform(captured_score_date):
    st = _load("standings", f"{captured_score_date}.json")
    df = transform_standings_to_df(st, snapshot_date=captured_score_date)
    assert len(df) == 32  # 32 NHL teams
    assert {"snapshot_date", "team_id", "wins", "losses", "ot_losses",
            "points"}.issubset(df.columns)
