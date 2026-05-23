"""RunsTable: chunk-level run log for resumable syncs.

One row per (chunk_start, chunk_end, chunk_kind) per attempt. status flips
to 'success' only after all lockstep sub-tables write cleanly. '--resume'
skips chunks recorded as 'success' or 'empty'.
"""

from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from google.cloud import bigquery

from nhl_bigquery.writer import TableRef

log = logging.getLogger(__name__)


class RunsTableRef(TableRef):
    pass


def iter_chunks(start: str, end: str, kind: str) -> list[tuple[str, str]]:
    """Split [start, end] into chunks by kind.

    kind='range'  → single chunk [(start, end)]
    kind='year'   → one chunk per calendar year
    kind='month'  → one chunk per calendar month
    Raises ValueError for unknown kind.
    """
    s = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end, "%Y-%m-%d").date()
    if kind == "range":
        return [(s.isoformat(), e.isoformat())]
    chunks: list[tuple[str, str]] = []
    cur = s
    while cur <= e:
        if kind == "year":
            period_end = date(cur.year, 12, 31)
        elif kind == "month":
            last_day = calendar.monthrange(cur.year, cur.month)[1]
            period_end = date(cur.year, cur.month, last_day)
        else:
            raise ValueError(f"unknown chunk kind: {kind!r}")
        last = min(period_end, e)
        chunks.append((cur.isoformat(), last.isoformat()))
        cur = last + timedelta(days=1)
    return chunks


@dataclass
class RunsTable:
    client: bigquery.Client

    def create_table_if_missing(self, ref: RunsTableRef) -> None:
        try:
            self.client.get_table(str(ref))
            return
        except Exception:
            pass
        schema = [
            bigquery.SchemaField("chunk_start", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("chunk_end", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("chunk_kind", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("table_kind", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("rows_written_plays", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("rows_written_games", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("rows_written_officials", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("rows_written_boxscore", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("rows_written_shifts", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("rows_written_standings", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("error", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("run_at", "TIMESTAMP", mode="REQUIRED"),
        ]
        self.client.create_table(bigquery.Table(str(ref), schema=schema))
        log.info("created runs table %s", ref)

    def completed_chunks(self, *, ref: RunsTableRef) -> set[tuple[date, date]]:
        sql = (
            f"SELECT chunk_start, chunk_end FROM `{ref}` "
            f"WHERE status IN ('success', 'empty')"
        )
        rows = list(self.client.query(sql).result())
        return {(r.chunk_start, r.chunk_end) for r in rows}

    def record_success(
        self,
        *,
        ref: RunsTableRef,
        chunk_start: date,
        chunk_end: date,
        chunk_kind: str,
        rows_written: dict[str, int],
    ) -> None:
        self._record(
            ref=ref,
            chunk_start=chunk_start,
            chunk_end=chunk_end,
            chunk_kind=chunk_kind,
            status="success",
            rows_written=rows_written,
            error=None,
        )

    def record_empty(
        self,
        *,
        ref: RunsTableRef,
        chunk_start: date,
        chunk_end: date,
        chunk_kind: str,
    ) -> None:
        self._record(
            ref=ref,
            chunk_start=chunk_start,
            chunk_end=chunk_end,
            chunk_kind=chunk_kind,
            status="empty",
            rows_written={},
            error=None,
        )

    def record_failed(
        self,
        *,
        ref: RunsTableRef,
        chunk_start: date,
        chunk_end: date,
        chunk_kind: str,
        error: str,
    ) -> None:
        self._record(
            ref=ref,
            chunk_start=chunk_start,
            chunk_end=chunk_end,
            chunk_kind=chunk_kind,
            status="failed",
            rows_written={},
            error=error,
        )

    def _record(
        self,
        *,
        ref: RunsTableRef,
        chunk_start: date,
        chunk_end: date,
        chunk_kind: str,
        status: str,
        rows_written: dict[str, int],
        error: str | None,
    ) -> None:
        row = {
            "chunk_start": chunk_start.isoformat(),
            "chunk_end": chunk_end.isoformat(),
            "chunk_kind": chunk_kind,
            "table_kind": "lockstep",
            "status": status,
            "rows_written_plays": rows_written.get("plays"),
            "rows_written_games": rows_written.get("games"),
            "rows_written_officials": rows_written.get("officials"),
            "rows_written_boxscore": rows_written.get("boxscore"),
            "rows_written_shifts": rows_written.get("shifts"),
            "rows_written_standings": rows_written.get("standings"),
            "error": error,
            "run_at": datetime.now(UTC).isoformat(),
        }
        errors = self.client.insert_rows_json(str(ref), [row])
        if errors:
            log.warning("runs insert errors: %s", errors)
