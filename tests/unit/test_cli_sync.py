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


def test_dry_run_does_not_call_writers():
    with patch("nhl_bigquery.cli.bigquery.Client") as mock_client, \
         patch("nhl_bigquery.cli.NHLAPIClient") as mock_api:
        ret = main([
            "sync", "--start", "2024-10-01", "--end", "2024-10-01",
            "--plays-table", "p.d.nhl_plays", "--dry-run",
        ])
        assert ret == 0
        # Should not have called the NHL API in dry-run
        mock_api.return_value.get_score.assert_not_called()
