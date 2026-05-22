# tests/unit/test_verify_internal.py
from unittest.mock import MagicMock

from nhl_bigquery.verify.internal import INTERNAL_CHECKS, run_internal_checks


def test_eight_checks_registered():
    expected = {
        "on_ice_skater_count_valid",
        "no_orphan_event_player",
        "score_monotonic",
        "period_time_in_bounds",
        "coords_in_bounds_or_null",
        "no_duplicate_events",
        "no_future_games",
        "shifts_valid_intervals",
    }
    assert set(INTERNAL_CHECKS.keys()) == expected


def test_run_checks_returns_pass_when_all_zero_violations():
    client = MagicMock()
    row = MagicMock()
    row.violations = 0
    row.total = 1000
    client.query.return_value.result.return_value = [row]

    result = run_internal_checks(client=client, plays_table="p.d.nhl_plays",
                                  shifts_table="p.d.shifts",
                                  games_table="p.d.games")
    assert result.overall_pass


def test_run_checks_fails_when_any_check_has_violations():
    client = MagicMock()
    bad = MagicMock()
    bad.violations = 5
    bad.total = 100
    good = MagicMock()
    good.violations = 0
    good.total = 100
    # First check returns bad, all others good
    responses_iter = iter([bad, good, good, good, good, good, good, good])
    client.query.return_value.result.side_effect = lambda: [next(responses_iter)]

    result = run_internal_checks(client=client, plays_table="p.d.nhl_plays",
                                  shifts_table="p.d.shifts",
                                  games_table="p.d.games")
    assert not result.overall_pass
