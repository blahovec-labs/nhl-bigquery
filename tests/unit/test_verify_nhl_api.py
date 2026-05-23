"""Unit tests for nhl_bigquery.verify.nhl_api — uses mocked clients only."""

from unittest.mock import MagicMock

from nhl_bigquery.verify.nhl_api import (
    verify_player_season,
    verify_team_season,
)


def test_verify_team_season_smoke():
    # Both sides report matching numbers → all metrics pass
    client = MagicMock()
    row = MagicMock()
    row.team_id = 10
    row.wins = 50
    row.losses = 25
    row.ot_losses = 7
    row.points = 107
    row.goal_for = 250
    row.goal_against = 200
    client.query.return_value.result.return_value = [row]

    api_client = MagicMock()
    api_client.get_standings.return_value = {
        "standings": [{"teamAbbrev": {"id": 10, "default": "TOR"},
                       "wins": 50, "losses": 25, "otLosses": 7,
                       "points": 107, "goalFor": 250, "goalAgainst": 200,
                       "teamName": {"default": "TOR"},
                       "conferenceName": "E", "divisionName": "Atlantic",
                       "gamesPlayed": 82, "goalDifferential": 50,
                       "regulationWins": 30, "regulationPlusOtWins": 45}],
    }
    result = verify_team_season(client=client, api=api_client,
                                table="p.d.nhl_plays", season=2024)
    assert result.overall_pass


def test_verify_player_season_smoke():
    client = MagicMock()
    row = MagicMock()
    row.player_id = 8478402
    row.goals = 60
    row.assists = 80
    client.query.return_value.result.return_value = [row]

    api_client = MagicMock()
    api_client._get.return_value = {
        "seasonTotals": [{"season": 20242025, "goals": 60, "assists": 80,
                          "leagueAbbrev": "NHL", "gameTypeId": 2}],
    }
    result = verify_player_season(client=client, api=api_client,
                                  table="p.d.nhl_plays", season=2024,
                                  metrics=["goals", "assists"])
    assert result.overall_pass
