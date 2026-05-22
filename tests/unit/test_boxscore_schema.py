# tests/unit/test_boxscore_schema.py
from nhl_bigquery.boxscore.schema import BOXSCORE_SCHEMA, get_partitioning


def test_partitioning():
    p = get_partitioning()
    assert p.clustering == ["player_id", "team_id"]


def test_skater_and_goalie_columns_present():
    names = {c.name for c in BOXSCORE_SCHEMA}
    skater_cols = {"goals", "assists", "points", "plus_minus", "pim", "hits",
                   "blocked_shots", "shots", "faceoffs", "faceoff_winning_pctg",
                   "power_play_goals", "power_play_points", "shorthanded_goals",
                   "sh_points", "power_play_toi", "shorthanded_toi", "toi"}
    goalie_cols = {"shots_against", "saves", "save_pctg", "goals_against",
                   "even_strength_shots_against", "power_play_shots_against",
                   "shorthanded_shots_against",
                   "even_strength_goals_against", "power_play_goals_against",
                   "shorthanded_goals_against"}
    common = {"game_id", "game_date", "player_id", "team_id",
              "player_position_category", "position_code", "sweater_number",
              "ingested_at"}
    assert skater_cols.issubset(names), f"missing skater: {skater_cols - names}"
    assert goalie_cols.issubset(names), f"missing goalie: {goalie_cols - names}"
    assert common.issubset(names), f"missing common: {common - names}"


def test_position_category_valid_values():
    spec = next(c for c in BOXSCORE_SCHEMA if c.name == "player_position_category")
    assert set(spec.valid_values or []) == {"skater", "goalie"}
