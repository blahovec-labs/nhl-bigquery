# tests/unit/test_plays_merge.py
from nhl_bigquery.plays.merge import (
    build_on_ice_at_event,
    parse_shifts,
)


def _shift(player_id, team_id, period, start, end, num=1):
    return {
        "playerId": player_id, "teamId": team_id,
        "period": period, "startTime": start, "endTime": end,
        "shiftNumber": num,
    }


def test_parse_shifts_basic():
    raw = [_shift(1, 10, 1, "0:00", "0:30")]
    parsed = parse_shifts(raw)
    assert parsed[0]["player_id"] == 1
    assert parsed[0]["team_id"] == 10
    assert parsed[0]["start_abs_seconds"] == 0
    assert parsed[0]["end_abs_seconds"] == 30


def test_player_on_ice_during_shift():
    shifts = parse_shifts([_shift(1, 10, 1, "0:00", "1:00")])
    result = build_on_ice_at_event(shifts, event_abs_seconds=30,
                                   home_team_id=10, away_team_id=20)
    assert 1 in result.home_on_ice_ids
    assert result.away_on_ice_ids == []


def test_player_not_on_ice_outside_shift():
    shifts = parse_shifts([_shift(1, 10, 1, "0:00", "1:00")])
    result = build_on_ice_at_event(shifts, event_abs_seconds=120,
                                   home_team_id=10, away_team_id=20)
    assert 1 not in result.home_on_ice_ids


def test_half_open_interval_player_not_on_ice_at_end():
    # Shift ends at exactly t=60. At t=60 the player is NOT on ice.
    shifts = parse_shifts([_shift(1, 10, 1, "0:00", "1:00")])
    result = build_on_ice_at_event(shifts, event_abs_seconds=60,
                                   home_team_id=10, away_team_id=20)
    assert 1 not in result.home_on_ice_ids


def test_half_open_interval_player_on_ice_at_start():
    # Shift starts at exactly t=60. At t=60 the player IS on ice.
    shifts = parse_shifts([_shift(1, 10, 1, "1:00", "1:30")])
    result = build_on_ice_at_event(shifts, event_abs_seconds=60,
                                   home_team_id=10, away_team_id=20)
    assert 1 in result.home_on_ice_ids


def test_split_by_team():
    shifts = parse_shifts([
        _shift(1, 10, 1, "0:00", "1:00"),
        _shift(2, 20, 1, "0:00", "1:00"),
        _shift(3, 10, 1, "0:00", "1:00"),
    ])
    result = build_on_ice_at_event(shifts, event_abs_seconds=30,
                                   home_team_id=10, away_team_id=20)
    assert set(result.home_on_ice_ids) == {1, 3}
    assert set(result.away_on_ice_ids) == {2}


def test_event_abs_seconds_none_returns_empty():
    shifts = parse_shifts([_shift(1, 10, 1, "0:00", "1:00")])
    result = build_on_ice_at_event(shifts, event_abs_seconds=None,
                                   home_team_id=10, away_team_id=20)
    assert result.home_on_ice_ids == []
    assert result.away_on_ice_ids == []
    assert result.source_quality == "FULL"  # SO does not change source_quality


def test_empty_shifts_returns_no_shifts_quality():
    result = build_on_ice_at_event([], event_abs_seconds=30,
                                   home_team_id=10, away_team_id=20)
    assert result.home_on_ice_ids == []
    assert result.away_on_ice_ids == []
    assert result.source_quality == "NO_SHIFTS"
