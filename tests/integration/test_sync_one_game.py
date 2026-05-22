"""Integration smoke test: sync --dry-run exits 0 without touching BQ."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import responses as responses_lib

from nhl_bigquery.cli import main

FIXTURES = Path(__file__).parent.parent / "fixtures"


@responses_lib.activate
def test_sync_one_game_dry_run(captured_game_id, captured_score_date):
    """sync --dry-run should return 0 and never touch BigQuery.

    The responses decorator mocks HTTP but --dry-run exits before any
    API calls, so this is primarily a CLI argument-parsing sanity check.
    """
    date_to_fixture = {
        captured_score_date: FIXTURES / "score" / f"{captured_score_date}.json",
    }
    for date, path in date_to_fixture.items():
        responses_lib.add(
            responses_lib.GET,
            f"https://api-web.nhle.com/v1/score/{date}",
            json=json.loads(path.read_text(encoding="utf-8")),
            status=200,
        )

    ret = main([
        "sync",
        "--start", captured_score_date,
        "--end", captured_score_date,
        "--plays-table", "myproject.mydataset.nhl_plays",
        "--chunk-by", "range",
        "--dry-run",
    ])
    assert ret == 0
