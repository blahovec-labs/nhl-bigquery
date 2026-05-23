"""Render ColumnSpec lists into BQ descriptions, LLM context, dictionary,
markdown, and dbt YAML."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from google.cloud import bigquery

from nhl_bigquery.docs.taxonomy import TABLES, resolve_table_kind
from nhl_bigquery.schema import ColumnSpec


def _column_doc(spec: ColumnSpec) -> str:
    """Build a single descriptive string from all ColumnSpec metadata fields."""
    parts = [spec.business_definition]
    if spec.valid_values:
        parts.append(f"Valid values: {', '.join(spec.valid_values)}.")
    if spec.valid_range is not None:
        parts.append(f"Valid range: {spec.valid_range[0]} – {spec.valid_range[1]}.")
    if spec.example_value is not None:
        parts.append(f"Example: {spec.example_value!r}.")
    if spec.gotchas:
        parts.append(
            "Gotchas: " + " ".join(f"({i + 1}) {g}" for i, g in enumerate(spec.gotchas))
        )
    if spec.nhl_api_equivalent:
        parts.append(f"NHL API: {spec.nhl_api_equivalent}.")
    if spec.deprecated_in_year is not None:
        parts.append(f"Universally NULL from {spec.deprecated_in_year} onward.")
    return " ".join(parts)


def render_bq_descriptions(table_kind: str) -> list[bigquery.SchemaField]:
    """Build a list of BigQuery SchemaField for the chosen table.

    *table_kind* may be either a canonical TABLES key (e.g. ``"nhl_plays"``)
    or a short alias (e.g. ``"plays"``).  Each SchemaField carries a
    ``description`` assembled from the full ColumnSpec metadata, truncated to
    the 1 024-character BigQuery limit.
    """
    key = resolve_table_kind(table_kind)
    schema = TABLES[key]["schema"]
    return [
        bigquery.SchemaField(
            name=spec.name,
            field_type=spec.type,
            mode=spec.mode,
            description=_column_doc(spec)[:1024],
        )
        for spec in schema
    ]


def render_llm_context() -> str:
    """Return a single Markdown document with every column of every table.

    Includes business_definition, gotchas, valid_range, nhl_api_equivalent,
    and example values — intended to be injected into LLM system prompts.
    """
    lines = ["# nhl-bigquery — LLM context\n"]
    lines.append("Single-doc reference for every column in every table.\n")
    for tbl, meta in TABLES.items():
        lines.append(f"\n## Table `{tbl}`\n")
        p = meta["partitioning"]
        lines.append(
            f"Partitioned by `{p.field}` ({p.type}); "
            f"clustered by {', '.join(p.clustering)}.\n"
        )
        for spec in meta["schema"]:
            lines.append(f"### `{spec.name}` ({spec.type} {spec.mode})\n")
            lines.append(_column_doc(spec) + "\n")
    return "\n".join(lines)


def render_markdown() -> str:
    """Return a human-readable Markdown column reference grouped by table."""
    lines = ["# nhl-bigquery — Column Reference\n"]
    for tbl, meta in TABLES.items():
        lines.append(f"\n## `{tbl}`\n")
        lines.append("| Column | Type | Mode | Description |")
        lines.append("|---|---|---|---|")
        for spec in meta["schema"]:
            short = spec.short_description.replace("|", "\\|")
            lines.append(f"| `{spec.name}` | {spec.type} | {spec.mode} | {short} |")
    return "\n".join(lines)


def render_data_dictionary(*, dataset: str, table: str) -> list[dict[str, Any]]:
    """Return JSON-shaped rows matching the ``data_dictionary`` table schema.

    Each row records one column's full lineage, type, tags, and definitions.
    *table* must be a canonical TABLES key (e.g. ``"nhl_plays"``).
    """
    schema = TABLES[table]["schema"]
    now = datetime.now(UTC).isoformat()
    return [
        {
            "dataset": dataset,
            "table": table,
            "column": spec.name,
            "dtype": spec.type,
            "description": spec.short_description,
            "business_definition": _column_doc(spec),
            "owner": "nhl-bigquery",
            "tags": list(spec.semantic_tags),
            "source_system": "nhl-api",
            "upstream_lineage_json": json.dumps({
                "nhl_api_equivalent": spec.nhl_api_equivalent,
                "nhl_api_source_field": spec.nhl_api_source_field,
            }),
            "created_at": now,
            "updated_at": now,
        }
        for spec in schema
    ]


def apply_data_dictionary(
    *,
    client: bigquery.Client,
    dictionary_table: str,
    dataset: str,
    table: str,
) -> int:
    """Atomically replace rows for *(dataset, table)* in the dictionary table.

    Deletes existing rows for the (dataset, table) pair, then inserts fresh
    ones from :func:`render_data_dictionary`.  Returns the number of rows
    inserted.  Wired by Task 23.
    """
    rows = render_data_dictionary(dataset=dataset, table=table)
    delete_sql = (
        f"DELETE FROM `{dictionary_table}` "
        f"WHERE dataset = @ds AND `table` = @tbl"
    )
    client.query(
        delete_sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("ds", "STRING", dataset),
                bigquery.ScalarQueryParameter("tbl", "STRING", table),
            ]
        ),
    ).result()
    errors = client.insert_rows_json(dictionary_table, rows)
    if errors:
        raise RuntimeError(f"dictionary insert failed: {errors}")
    return len(rows)


def render_dbt_yaml() -> str:
    """Return a dbt YAML stub for all tables.

    Generates ``version: 2`` format with one model block per table and one
    column entry per ColumnSpec.
    """
    lines = ["version: 2", "", "models:"]
    for tbl, meta in TABLES.items():
        lines.append(f"  - name: {tbl}")
        lines.append(f'    description: "nhl-bigquery {tbl} table"')
        lines.append("    columns:")
        for spec in meta["schema"]:
            short = spec.short_description.replace('"', "'")
            lines.append(f"      - name: {spec.name}")
            lines.append(f'        description: "{short}"')
    return "\n".join(lines) + "\n"
