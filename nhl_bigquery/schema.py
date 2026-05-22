"""ColumnSpec dataclass + shared primitives for table schemas.

A ColumnSpec is the single source of truth for one column: BQ type,
mode, business definition, gotchas, and lineage to the NHL API field.
Five doc renderers read these to produce bq-apply / llm / dictionary /
markdown / dbt outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SCHEMA_VERSION = "0.1.0"

BqType = Literal[
    "INT64",
    "FLOAT64",
    "STRING",
    "BOOL",
    "DATE",
    "TIMESTAMP",
    "TIME",
    "NUMERIC",
]
BqMode = Literal["REQUIRED", "NULLABLE", "REPEATED"]

_VALID_TYPES = set(BqType.__args__)  # type: ignore[attr-defined]
_VALID_MODES = set(BqMode.__args__)  # type: ignore[attr-defined]


@dataclass(frozen=True)
class ColumnSpec:
    """Single source of truth for one column in an `nhl_bigquery` table."""

    name: str
    type: BqType
    mode: BqMode
    short_description: str
    business_definition: str
    semantic_tags: list[str]
    valid_range: tuple[float, float] | None
    valid_values: list[str] | None
    example_value: object | None
    gotchas: list[str]
    nhl_api_equivalent: str | None
    nhl_api_source_field: str
    deprecated_in_year: int | None

    def __post_init__(self) -> None:
        if self.type not in _VALID_TYPES:
            raise ValueError(f"{self.name}: invalid type {self.type!r}")
        if self.mode not in _VALID_MODES:
            raise ValueError(f"{self.name}: invalid mode {self.mode!r}")
        if not self.business_definition.strip():
            raise ValueError(f"{self.name}: business_definition required")


@dataclass(frozen=True)
class PartitioningSpec:
    """BigQuery partitioning + clustering for one table."""

    field: str
    type: Literal["DAY", "MONTH", "YEAR"]
    clustering: list[str]
