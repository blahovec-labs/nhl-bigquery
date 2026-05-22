"""Unit tests for OFFICIALS_SCHEMA."""

import pytest

from nhl_bigquery.officials.schema import OFFICIALS_SCHEMA, get_partitioning


def test_partitioning():
    p = get_partitioning()
    assert p.field == "game_date"
    assert p.type == "DAY"
    assert p.clustering == ["game_id"]


def test_required_columns_present():
    names = [col.name for col in OFFICIALS_SCHEMA]
    assert names == ["game_id", "game_date", "role", "official_name", "official_number", "ingested_at"]


def test_role_valid_values():
    role_col = next(col for col in OFFICIALS_SCHEMA if col.name == "role")
    assert role_col.mode == "REQUIRED"
    assert role_col.valid_values == ["REFEREE_1", "REFEREE_2", "LINESMAN_1", "LINESMAN_2"]
