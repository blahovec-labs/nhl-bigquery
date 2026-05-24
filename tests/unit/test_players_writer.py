"""dim_players upsert writer tests (mocked BigQuery client)."""

from unittest.mock import MagicMock

import pandas as pd

from nhl_bigquery.players.writer import (
    build_merge_sql,
    select_missing_player_ids_sql,
    upsert_players,
)


def test_build_merge_sql_uses_target_and_temp_refs():
    sql = build_merge_sql(
        target="proj.ds.dim_players",
        source="proj.ds._dim_players_stage_abc",
    )
    assert "MERGE `proj.ds.dim_players`" in sql
    assert "USING `proj.ds._dim_players_stage_abc`" in sql
    assert "ON t.player_id = s.player_id" in sql
    assert "WHEN MATCHED THEN UPDATE SET" in sql
    assert "first_name = s.first_name" in sql
    assert "WHEN NOT MATCHED THEN INSERT" in sql


def test_select_missing_player_ids_sql_unions_role_columns_and_arrays():
    sql = select_missing_player_ids_sql(
        plays_table="proj.ds.nhl_plays",
        players_table="proj.ds.dim_players",
    )
    assert "SELECT shooter_id" in sql
    assert "SELECT scorer_id" in sql
    assert "UNNEST(home_on_ice_ids)" in sql
    assert "UNNEST(away_on_ice_ids)" in sql
    assert "LEFT JOIN `proj.ds.dim_players`" in sql or "NOT IN" in sql or "NOT EXISTS" in sql


def test_upsert_players_skips_empty_df():
    bq = MagicMock()
    n = upsert_players(bq, target="proj.ds.dim_players", df=pd.DataFrame())
    assert n == 0
    bq.load_table_from_dataframe.assert_not_called()


def test_upsert_players_writes_then_merges_then_drops_temp():
    bq = MagicMock()
    load_job = MagicMock()
    load_job.result.return_value = None
    bq.load_table_from_dataframe.return_value = load_job

    query_job = MagicMock()
    query_job.result.return_value = None
    bq.query.return_value = query_job

    df = pd.DataFrame([{"player_id": 1, "first_name": "A", "full_name": "A"}])
    n = upsert_players(bq, target="proj.ds.dim_players", df=df)
    assert n == 1

    # Sequence: load (to staging) → MERGE → DROP TABLE staging
    bq.load_table_from_dataframe.assert_called_once()
    assert bq.query.call_count == 2  # MERGE + DROP TABLE
    sql_calls = [c.args[0] for c in bq.query.call_args_list]
    assert any("MERGE" in s for s in sql_calls)
    assert any("DROP TABLE" in s for s in sql_calls)
