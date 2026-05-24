"""Tests for transform_player_landing_to_row."""

import json
from pathlib import Path

import pandas as pd

from nhl_bigquery.players.transform import (
    transform_player_landing_to_row,
    transform_player_landings_to_df,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "players"


def _load(player_id: int) -> dict:
    return json.loads((FIXTURES / f"{player_id}.json").read_text(encoding="utf-8"))


def test_transform_skater_row():
    row = transform_player_landing_to_row(_load(8478402))
    assert row["player_id"] == 8478402
    assert row["first_name"] == "Connor"
    assert row["last_name"] == "McDavid"
    assert row["full_name"] == "Connor McDavid"
    assert row["position_code"] == "C"
    assert row["sweater_number"] == 97
    assert row["current_team_abbrev"] == "EDM"
    assert row["shoots_catches"] == "L"
    assert row["height_inches"] == 73
    assert row["weight_pounds"] == 193
    assert row["ingested_at"] is not None


def test_transform_goalie_row():
    row = transform_player_landing_to_row(_load(8473419))
    assert row["position_code"] == "G"
    assert row["sweater_number"] == 29


def test_transform_handles_missing_optional_fields():
    minimal = {"playerId": 1234567, "firstName": {"default": "Foo"}, "lastName": {"default": "Bar"}}
    row = transform_player_landing_to_row(minimal)
    assert row["player_id"] == 1234567
    assert row["full_name"] == "Foo Bar"
    assert row["position_code"] is None
    assert row["sweater_number"] is None


def test_transform_landings_to_df_concatenates():
    landings = [_load(8478402), _load(8473419)]
    df = transform_player_landings_to_df(landings)
    assert len(df) == 2
    assert set(df["player_id"]) == {8478402, 8473419}
