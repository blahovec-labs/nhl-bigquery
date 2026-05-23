# tests/unit/test_cli_sync.py
from unittest.mock import patch

from nhl_bigquery.cli import build_parser, main


def test_parser_accepts_sync_args():
    parser = build_parser()
    ns = parser.parse_args([
        "sync", "--start", "2024-10-01", "--end", "2024-10-31",
        "--plays-table", "p.d.nhl_plays",
        "--dry-run",
    ])
    assert ns.command == "sync"
    assert ns.start == "2024-10-01"
    assert ns.plays_table == "p.d.nhl_plays"
    assert ns.dry_run is True
    assert ns.chunk_by == "month"


def test_parser_skip_flags():
    parser = build_parser()
    ns = parser.parse_args([
        "sync", "--start", "2024-10-01", "--end", "2024-10-31",
        "--plays-table", "p.d.nhl_plays",
        "--skip-games", "--skip-officials",
    ])
    assert ns.skip_games is True
    assert ns.skip_officials is True
    assert ns.skip_shifts is False


def test_sleep_seconds_flag():
    parser = build_parser()
    ns = parser.parse_args([
        "sync", "--start", "2024-10-01", "--end", "2024-10-01",
        "--plays-table", "p.d.nhl_plays",
        "--sleep-seconds", "0.5",
    ])
    assert ns.sleep_seconds == 0.5

    ns_default = parser.parse_args([
        "sync", "--start", "2024-10-01", "--end", "2024-10-01",
        "--plays-table", "p.d.nhl_plays",
    ])
    assert ns_default.sleep_seconds == 1.0


def test_dry_run_does_not_call_writers():
    with patch("nhl_bigquery.cli.bigquery.Client"), \
         patch("nhl_bigquery.cli.NHLAPIClient") as mock_api:
        ret = main([
            "sync", "--start", "2024-10-01", "--end", "2024-10-01",
            "--plays-table", "p.d.nhl_plays", "--dry-run",
        ])
        assert ret == 0
        # Should not have called the NHL API in dry-run
        mock_api.return_value.get_score.assert_not_called()


def test_include_preseason_default_false():
    parser = build_parser()
    ns = parser.parse_args([
        "sync", "--start", "2024-10-01", "--end", "2024-10-01",
        "--plays-table", "p.d.nhl_plays",
    ])
    assert ns.include_preseason is False


def test_include_preseason_flag_true():
    parser = build_parser()
    ns = parser.parse_args([
        "sync", "--start", "2024-10-01", "--end", "2024-10-01",
        "--plays-table", "p.d.nhl_plays",
        "--include-preseason",
    ])
    assert ns.include_preseason is True


def test_per_game_error_tolerance():
    """A single game raising during fetch must not crash the chunk."""
    # Two regular-season games seen by /score; one's get_landing raises.
    _common_team_fields = {
        "homeTeam": {"id": 10, "abbrev": "TOR", "score": 0},
        "awayTeam": {"id": 6, "abbrev": "BOS", "score": 0},
        "season": 20242025,
        "venue": {"default": "Test Arena"},
    }
    score_payload = {
        "games": [
            {"id": 2024020001, "gameType": 2, "gameDate": "2024-10-08", **_common_team_fields},
            {"id": 2024020002, "gameType": 2, "gameDate": "2024-10-08", **_common_team_fields},
        ],
    }

    def get_landing_side_effect(game_id):
        if game_id == 2024020001:
            raise RuntimeError("simulated 500 on landing")
        return {"id": game_id, "gameDate": "2024-10-08",
                "homeTeam": {"id": 10, "abbrev": "TOR"},
                "awayTeam": {"id": 6, "abbrev": "BOS"},
                "season": 20242025, "gameType": 2}

    with patch("nhl_bigquery.cli.bigquery.Client"), \
         patch("nhl_bigquery.cli.NHLAPIClient") as mock_api, \
         patch("nhl_bigquery.cli.BigQueryWriter"), \
         patch("nhl_bigquery.cli.RunsTable") as mock_runs_cls, \
         patch("nhl_bigquery.cli.iter_chunks", return_value=[("2024-10-08", "2024-10-08")]):
        api = mock_api.return_value
        api.get_score.return_value = score_payload
        api.get_standings.return_value = {"standings": []}
        api.get_play_by_play.return_value = {"id": 1, "plays": [],
                                              "homeTeam": {"id": 10, "abbrev": "TOR"},
                                              "awayTeam": {"id": 6, "abbrev": "BOS"},
                                              "season": 20242025, "gameType": 2,
                                              "gameDate": "2024-10-08"}
        api.get_shift_charts.return_value = {"data": []}
        api.get_boxscore.return_value = {"id": 1, "gameDate": "2024-10-08",
                                          "homeTeam": {"id": 10}, "awayTeam": {"id": 6},
                                          "playerByGameStats": {}}
        api.get_right_rail.return_value = {"gameInfo": {}}
        api.get_landing.side_effect = get_landing_side_effect

        runs = mock_runs_cls.return_value
        runs.completed_chunks.return_value = set()

        ret = main([
            "sync", "--start", "2024-10-08", "--end", "2024-10-08",
            "--plays-table", "p.d.nhl_plays",
            "--chunk-by", "range",
            "--sleep-seconds", "0",
            "--skip-shifts", "--skip-standings",
        ])

        assert ret == 0
        # Both games attempted; one raised, one succeeded; chunk did NOT crash.
        assert api.get_landing.call_count == 2
        # Chunk recorded as success (the surviving game wrote rows)
        # OR empty (if no rows landed); either way, no failed record from the
        # chunk-level exception path.
        assert not runs.record_failed.called
