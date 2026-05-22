# tests/unit/test_strength_state.py
from nhl_bigquery.plays.strength import derive_strength_state


def test_even_strength_5v5():
    assert derive_strength_state(home_skaters=5, away_skaters=5,
                                 home_goalie=True, away_goalie=True) == "EV"


def test_home_power_play_5v4():
    assert derive_strength_state(home_skaters=5, away_skaters=4,
                                 home_goalie=True, away_goalie=True) == "PP_H"


def test_away_power_play_4v5():
    assert derive_strength_state(home_skaters=4, away_skaters=5,
                                 home_goalie=True, away_goalie=True) == "PP_A"


def test_home_shorthanded_is_same_as_away_power_play():
    # Same on-ice state, but SH labels go to the disadvantaged side
    # Choice: prefer PP_A over SH_H (one canonical label per state)
    assert derive_strength_state(home_skaters=4, away_skaters=5,
                                 home_goalie=True, away_goalie=True) == "PP_A"


def test_3v3_ot():
    assert derive_strength_state(home_skaters=3, away_skaters=3,
                                 home_goalie=True, away_goalie=True) == "3v3"


def test_4v4_coincidental_majors():
    assert derive_strength_state(home_skaters=4, away_skaters=4,
                                 home_goalie=True, away_goalie=True) == "4v4"


def test_home_empty_net_extra_attacker():
    # Home pulls goalie, 6 skaters vs 5
    assert derive_strength_state(home_skaters=6, away_skaters=5,
                                 home_goalie=False, away_goalie=True) == "EN_H"


def test_away_empty_net():
    assert derive_strength_state(home_skaters=5, away_skaters=6,
                                 home_goalie=True, away_goalie=False) == "EN_A"


def test_shorthanded_home_4v5_relabeled_as_pp_a():
    # SH on home side = PP on away side. Canonical label: PP_A.
    assert derive_strength_state(home_skaters=4, away_skaters=5,
                                 home_goalie=True, away_goalie=True) == "PP_A"


def test_handles_zero_skaters_returns_none():
    assert derive_strength_state(home_skaters=0, away_skaters=5,
                                 home_goalie=True, away_goalie=True) is None
