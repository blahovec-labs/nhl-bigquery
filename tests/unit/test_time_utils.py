import pytest

from nhl_bigquery.time_utils import event_abs_seconds, parse_mmss


def test_parse_mmss_basic():
    assert parse_mmss("0:00") == 0
    assert parse_mmss("1:30") == 90
    assert parse_mmss("19:59") == 19 * 60 + 59
    assert parse_mmss("20:00") == 1200


def test_parse_mmss_strips_whitespace():
    assert parse_mmss("  5:00  ") == 300


def test_parse_mmss_rejects_malformed():
    with pytest.raises(ValueError):
        parse_mmss("5")
    with pytest.raises(ValueError):
        parse_mmss("")
    with pytest.raises(ValueError):
        parse_mmss("5:60")


def test_parse_mmss_none_returns_none():
    assert parse_mmss(None) is None


def test_event_abs_seconds_period_1():
    assert event_abs_seconds(period=1, time_in_period="5:00") == 300


def test_event_abs_seconds_period_3_end():
    # End of regulation: period 3, 20:00 elapsed → 3600s
    assert event_abs_seconds(period=3, time_in_period="20:00") == 3600


def test_event_abs_seconds_ot_regular_season():
    # Regular-season OT is period 4; OT only lasts 5 minutes (300s)
    # but offset math still uses 1200 per period
    assert event_abs_seconds(period=4, time_in_period="3:45") == 3600 + 225


def test_event_abs_seconds_shootout_returns_none():
    # Shootout has no real time; period_type SO should yield None
    assert event_abs_seconds(period=5, time_in_period=None) is None
