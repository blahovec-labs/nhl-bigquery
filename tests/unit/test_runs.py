# tests/unit/test_runs.py
from datetime import date
from unittest.mock import MagicMock

from nhl_bigquery.runs import RunsTable, RunsTableRef, iter_chunks


def test_iter_chunks_year():
    chunks = iter_chunks("2024-01-01", "2024-12-31", kind="year")
    assert chunks == [("2024-01-01", "2024-12-31")]


def test_iter_chunks_month():
    chunks = iter_chunks("2024-10-01", "2024-12-15", kind="month")
    assert chunks == [
        ("2024-10-01", "2024-10-31"),
        ("2024-11-01", "2024-11-30"),
        ("2024-12-01", "2024-12-15"),
    ]


def test_iter_chunks_range():
    chunks = iter_chunks("2024-10-08", "2024-10-12", kind="range")
    assert chunks == [("2024-10-08", "2024-10-12")]


def test_runs_table_completed_chunks_returns_set():
    client = MagicMock()
    row = MagicMock()
    row.chunk_start = date(2024, 10, 1)
    row.chunk_end = date(2024, 10, 31)
    client.query.return_value.result.return_value = [row]

    runs = RunsTable(client=client)
    ref = RunsTableRef("p", "d", "_nhl_ingest_runs")
    completed = runs.completed_chunks(ref=ref)
    assert (date(2024, 10, 1), date(2024, 10, 31)) in completed
