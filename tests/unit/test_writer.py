# tests/unit/test_writer.py
from unittest.mock import MagicMock

import pandas as pd
import pytest

from nhl_bigquery.writer import BigQueryWriter, TableRef


def test_tableref_parse():
    ref = TableRef.parse("myproject.mydataset.mytable")
    assert ref.project == "myproject"
    assert ref.dataset == "mydataset"
    assert ref.table == "mytable"
    assert str(ref) == "myproject.mydataset.mytable"


def test_tableref_parse_rejects_malformed():
    with pytest.raises(ValueError):
        TableRef.parse("not.enough")
    with pytest.raises(ValueError):
        TableRef.parse("a.b.c.d")


def test_writer_deletes_then_inserts_for_chunk():
    client = MagicMock()
    writer = BigQueryWriter(client=client)
    ref = TableRef("p", "d", "t")
    df = pd.DataFrame([{"game_date": "2024-10-08", "game_id": 1, "x": 1}])

    writer.write(ref, df, partition_field="game_date",
                 chunk_start="2024-10-01", chunk_end="2024-10-31")

    # Should have issued a DELETE query for the chunk window
    delete_calls = [c for c in client.query.call_args_list
                    if "DELETE" in str(c).upper()]
    assert delete_calls, "expected a DELETE query for the chunk"
    # Should have issued a load via load_table_from_dataframe
    assert client.load_table_from_dataframe.called


def test_writer_skips_write_when_dataframe_empty():
    client = MagicMock()
    writer = BigQueryWriter(client=client)
    ref = TableRef("p", "d", "t")
    df = pd.DataFrame()

    n = writer.write(ref, df, partition_field="game_date",
                     chunk_start="2024-10-01", chunk_end="2024-10-31")

    assert n == 0
    assert not client.load_table_from_dataframe.called
