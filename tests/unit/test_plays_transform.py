import json
from pathlib import Path

import pandas as pd

from nhl_bigquery.plays.transform import transform_game_to_plays_df

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(game_id: int, kind: str) -> dict:
    path = FIXTURES / "games" / str(game_id) / f"{kind}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_transform_returns_dataframe_with_expected_columns(captured_game_id):
    pbp = _load(captured_game_id, "play-by-play")
    shifts = _load(captured_game_id, "shift-charts")
    landing = _load(captured_game_id, "landing")

    df = transform_game_to_plays_df(pbp=pbp, shift_charts=shifts, landing=landing)

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    expected_cols = {
        "game_id", "event_id", "event_type", "period", "period_type",
        "time_in_period", "event_abs_seconds",
        "home_on_ice_ids", "away_on_ice_ids", "source_quality",
        "home_team_id", "away_team_id", "game_date",
    }
    assert expected_cols.issubset(set(df.columns))


def test_shootout_events_have_empty_on_ice(captured_game_id_shootout):
    pbp = _load(captured_game_id_shootout, "play-by-play")
    shifts = _load(captured_game_id_shootout, "shift-charts")
    landing = _load(captured_game_id_shootout, "landing")

    df = transform_game_to_plays_df(pbp=pbp, shift_charts=shifts, landing=landing)
    so = df[df["period_type"] == "SO"]
    assert len(so) > 0
    for _, row in so.iterrows():
        assert row["home_on_ice_ids"] == []
        assert row["away_on_ice_ids"] == []


def test_source_quality_full_when_shifts_present(captured_game_id):
    pbp = _load(captured_game_id, "play-by-play")
    shifts = _load(captured_game_id, "shift-charts")
    landing = _load(captured_game_id, "landing")
    df = transform_game_to_plays_df(pbp=pbp, shift_charts=shifts, landing=landing)
    non_so = df[df["period_type"] != "SO"]
    assert (non_so["source_quality"] == "FULL").all()


def test_no_shifts_produces_no_shifts_quality():
    pbp = {
        "id": 9999999999,
        "gameDate": "2024-10-08",
        "homeTeam": {"id": 10, "abbrev": "TOR"},
        "awayTeam": {"id": 6, "abbrev": "BOS"},
        "season": 20242025,
        "gameType": 2,
        "plays": [{
            "eventId": 1,
            "typeDescKey": "faceoff",
            "periodDescriptor": {"number": 1, "periodType": "REG"},
            "timeInPeriod": "0:00",
            "timeRemaining": "20:00",
            "sortOrder": 1,
            "details": {},
        }],
    }
    shifts = {"data": []}
    landing = {"id": 9999999999, "gameDate": "2024-10-08",
               "homeTeam": {"id": 10, "abbrev": "TOR"},
               "awayTeam": {"id": 6, "abbrev": "BOS"},
               "season": 20242025, "gameType": 2}
    df = transform_game_to_plays_df(pbp=pbp, shift_charts=shifts, landing=landing)
    assert (df["source_quality"] == "NO_SHIFTS").all()
