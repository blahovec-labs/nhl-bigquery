"""cmd_players routing tests with HTTP + BQ mocked."""

import argparse
from unittest.mock import MagicMock, patch

import pandas as pd

from nhl_bigquery.cli import cmd_players


def _ns(**overrides) -> argparse.Namespace:
    base = dict(
        command="players",
        players_table="proj.ds.dim_players",
        source="nhl-api",
        ids=None,
        from_plays_table=None,
        sleep_seconds=0.0,
        dry_run=False,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


@patch("nhl_bigquery.cli.bigquery.Client")
@patch("nhl_bigquery.cli.NHLAPIClient")
def test_players_explicit_ids_fetches_and_upserts(MockClient, MockBq):
    api = MockClient.return_value
    api.get_player_landing.side_effect = [
        {"playerId": 1, "firstName": {"default": "A"}, "lastName": {"default": "Z"}},
        {"playerId": 2, "firstName": {"default": "B"}, "lastName": {"default": "Y"}},
    ]
    bq_client = MockBq.return_value
    load_job = MagicMock(); load_job.result.return_value = None
    bq_client.load_table_from_dataframe.return_value = load_job
    bq_client.query.return_value = MagicMock(result=MagicMock(return_value=None))

    rc = cmd_players(_ns(source="nhl-api", ids="1,2"))
    assert rc == 0
    assert api.get_player_landing.call_count == 2


@patch("nhl_bigquery.cli.bigquery.Client")
@patch("nhl_bigquery.cli.NHLAPIClient")
def test_players_from_plays_discovers_ids_via_sql(MockClient, MockBq):
    api = MockClient.return_value
    api.get_player_landing.return_value = {
        "playerId": 42, "firstName": {"default": "X"}, "lastName": {"default": "Q"},
    }
    bq_client = MockBq.return_value
    bq_client.query.return_value.to_dataframe.return_value = pd.DataFrame({"player_id": [42]})
    load_job = MagicMock(); load_job.result.return_value = None
    bq_client.load_table_from_dataframe.return_value = load_job

    rc = cmd_players(_ns(
        source="from-plays",
        from_plays_table="proj.ds.nhl_plays",
    ))
    assert rc == 0
    # First .query() call is the discovery query.
    first_query = bq_client.query.call_args_list[0].args[0]
    assert "UNNEST(home_on_ice_ids)" in first_query


def test_players_rejects_ids_without_source_api():
    rc = cmd_players(_ns(source="from-plays", ids="1,2"))
    # --ids requires --source=nhl-api; mode misconfigured → fail.
    assert rc != 0


def test_players_dry_run_skips_writes(monkeypatch):
    captured = {"loaded": False}
    with patch("nhl_bigquery.cli.NHLAPIClient") as Mc, \
         patch("nhl_bigquery.cli.bigquery.Client") as Mb:
        Mc.return_value.get_player_landing.return_value = {
            "playerId": 1, "firstName": {"default": "A"}, "lastName": {"default": "Z"},
        }
        Mb.return_value.load_table_from_dataframe = lambda *a, **k: captured.update(loaded=True) or MagicMock(result=lambda: None)
        rc = cmd_players(_ns(source="nhl-api", ids="1", dry_run=True))
    assert rc == 0
    assert captured["loaded"] is False
