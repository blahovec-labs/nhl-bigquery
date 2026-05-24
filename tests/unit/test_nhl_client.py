import pytest
import responses

from nhl_bigquery.client import NHLAPIClient


@responses.activate
def test_get_play_by_play_success():
    responses.add(
        responses.GET,
        "https://api-web.nhle.com/v1/gamecenter/2024020001/play-by-play",
        json={"plays": [{"eventId": 1}]},
        status=200,
    )
    client = NHLAPIClient(sleep_seconds=0)
    result = client.get_play_by_play(2024020001)
    assert result == {"plays": [{"eventId": 1}]}


@responses.activate
def test_get_play_by_play_retries_on_500_then_succeeds():
    responses.add(responses.GET,
        "https://api-web.nhle.com/v1/gamecenter/2024020001/play-by-play",
        json={"error": "transient"}, status=500)
    responses.add(responses.GET,
        "https://api-web.nhle.com/v1/gamecenter/2024020001/play-by-play",
        json={"plays": []}, status=200)
    client = NHLAPIClient(sleep_seconds=0, max_retries=3)
    result = client.get_play_by_play(2024020001)
    assert result == {"plays": []}


@responses.activate
def test_get_play_by_play_raises_after_max_retries():
    for _ in range(5):
        responses.add(responses.GET,
            "https://api-web.nhle.com/v1/gamecenter/2024020001/play-by-play",
            json={"error": "x"}, status=500)
    client = NHLAPIClient(sleep_seconds=0, max_retries=3)
    with pytest.raises(Exception):
        client.get_play_by_play(2024020001)


@responses.activate
def test_get_score_for_date():
    responses.add(responses.GET,
        "https://api-web.nhle.com/v1/score/2024-10-08",
        json={"games": [{"id": 2024020001}]}, status=200)
    client = NHLAPIClient(sleep_seconds=0)
    assert client.get_score("2024-10-08") == {"games": [{"id": 2024020001}]}


@responses.activate
def test_get_standings_for_date():
    responses.add(responses.GET,
        "https://api-web.nhle.com/v1/standings/2024-10-08",
        json={"standings": []}, status=200)
    client = NHLAPIClient(sleep_seconds=0)
    assert client.get_standings("2024-10-08") == {"standings": []}


@responses.activate
def test_get_shift_charts_uses_legacy_endpoint():
    responses.add(responses.GET,
        "https://api.nhle.com/stats/rest/en/shiftcharts",
        json={"data": [{"playerId": 8478402, "shiftNumber": 1,
                        "period": 1, "startTime": "0:00", "endTime": "0:30"}],
              "total": 1},
        status=200,
        match=[responses.matchers.query_string_matcher("cayenneExp=gameId=2024020001")])
    client = NHLAPIClient(sleep_seconds=0)
    result = client.get_shift_charts(2024020001)
    assert result["total"] == 1
    assert result["data"][0]["playerId"] == 8478402


def test_get_player_landing_builds_correct_url(monkeypatch):
    from nhl_bigquery.client import NHLAPIClient

    captured = {}

    def fake_get(self, path):
        captured["path"] = path
        return {"playerId": 8478402, "firstName": {"default": "Connor"}}

    monkeypatch.setattr(NHLAPIClient, "_get", fake_get)
    client = NHLAPIClient(sleep_seconds=0)
    result = client.get_player_landing(8478402)
    assert captured["path"] == "/player/8478402/landing"
    assert result["playerId"] == 8478402
