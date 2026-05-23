"""BigQueryWriter + TableRef: idempotent chunked writes."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd
from google.cloud import bigquery

log = logging.getLogger(__name__)


def _coerce_df_for_bq(df: pd.DataFrame, schema: list[bigquery.SchemaField]) -> pd.DataFrame:
    """Coerce DataFrame columns to types that BigQuery load_table_from_dataframe accepts.

    BQ DATE columns must be datetime.date objects (not strings).
    BQ TIMESTAMP columns must be datetime-like (pd.Timestamp or datetime.datetime).
    BQ BOOL columns must be bool, not object.
    BQ INT64 / FLOAT64 columns must be numeric; non-numeric strings become NaN/None.
    """

    df = df.copy()
    schema_by_name = {f.name: f for f in schema}
    for col in df.columns:
        field = schema_by_name.get(col)
        if field is None:
            continue
        ft = field.field_type.upper()
        if ft == "DATE" and df[col].dtype == object:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        elif ft in ("TIMESTAMP", "DATETIME") and df[col].dtype == object:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
        elif ft == "BOOL" and df[col].dtype == object:
            df[col] = df[col].astype("boolean")
        elif ft in ("INT64", "INTEGER") and field.mode.upper() == "REPEATED":
            # REPEATED INT64: ensure each cell is a Python list of ints
            def _to_int_list(v: Any) -> list:
                if v is None:
                    return []
                if isinstance(v, list):
                    return [int(x) for x in v if x is not None]
                try:
                    import numpy as np
                    if isinstance(v, np.ndarray):
                        return [int(x) for x in v]
                except ImportError:
                    pass
                return list(v)
            df[col] = df[col].apply(_to_int_list)
        elif ft in ("INT64", "INTEGER") and df[col].dtype == object:
            # Coerce non-numeric strings (e.g. "0/0", "20:34") to NaN
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif ft in ("FLOAT64", "FLOAT", "NUMERIC") and df[col].dtype == object:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@dataclass(frozen=True)
class TableRef:
    project: str
    dataset: str
    table: str

    def __str__(self) -> str:
        return f"{self.project}.{self.dataset}.{self.table}"

    @classmethod
    def parse(cls, s: str) -> TableRef:
        parts = s.split(".")
        if len(parts) != 3:
            raise ValueError(f"expected project.dataset.table, got {s!r}")
        return cls(*parts)


class BigQueryWriter:
    """Idempotent chunked writer: deletes the chunk window, then inserts.

    The writer is agnostic to which table it writes — callers pass the
    `partition_field` (e.g. 'game_date' or 'snapshot_date'). For unpartitioned
    chunk boundaries (e.g. games), pass partition_field='game_date' as well.
    """

    def __init__(self, client: bigquery.Client | None = None) -> None:
        self.client = client or bigquery.Client()

    def create_table_if_missing(
        self,
        ref: TableRef,
        schema: list[bigquery.SchemaField],
        partition_field: str | None = None,
        clustering: list[str] | None = None,
    ) -> None:
        try:
            self.client.get_table(str(ref))
        except Exception:
            table = bigquery.Table(str(ref), schema=schema)
            if partition_field:
                table.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                    field=partition_field,
                )
            if clustering:
                table.clustering_fields = clustering
            self.client.create_table(table)
            log.info("created table %s", ref)

    def write(
        self,
        ref: TableRef,
        df: pd.DataFrame,
        *,
        partition_field: str,
        chunk_start: str,
        chunk_end: str,
    ) -> int:
        """Delete rows in [chunk_start, chunk_end] then insert df.

        Returns number of rows inserted (0 if df is empty).
        """
        if df.empty:
            log.info("write: empty df for %s, skipping", ref)
            return 0

        # Fetch the BQ table schema to coerce DataFrame column types before upload.
        try:
            bq_table = self.client.get_table(str(ref))
            bq_schema = list(bq_table.schema)
        except Exception:
            bq_schema = []

        delete_sql = (
            f"DELETE FROM `{ref}` "
            f"WHERE {partition_field} BETWEEN @start AND @end"
        )
        job = self.client.query(
            delete_sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("start", "DATE", chunk_start),
                    bigquery.ScalarQueryParameter("end", "DATE", chunk_end),
                ],
            ),
        )
        job.result()
        log.info("deleted rows in %s [%s, %s]", ref, chunk_start, chunk_end)

        if bq_schema:
            df = _coerce_df_for_bq(df, bq_schema)

        load_job = self.client.load_table_from_dataframe(
            df,
            str(ref),
            job_config=bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                schema=bq_schema if bq_schema else None,
            ),
        )
        load_job.result()
        log.info("inserted %d rows into %s", len(df), ref)
        return len(df)
