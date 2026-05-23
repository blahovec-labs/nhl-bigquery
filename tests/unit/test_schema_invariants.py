import pytest

from nhl_bigquery.schema import ColumnSpec, PartitioningSpec


def test_columnspec_validates_required_business_definition():
    with pytest.raises(ValueError, match="business_definition required"):
        ColumnSpec(
            name="x", type="INT64", mode="NULLABLE",
            short_description="x", business_definition="",
            semantic_tags=[], valid_range=None, valid_values=None,
            example_value=None, gotchas=[], nhl_api_equivalent=None,
            nhl_api_source_field="x", deprecated_in_year=None,
        )


def test_columnspec_rejects_unknown_type():
    with pytest.raises(ValueError, match="invalid type"):
        ColumnSpec(
            name="x", type="GUNK", mode="NULLABLE",  # type: ignore[arg-type]
            short_description="x", business_definition="x",
            semantic_tags=[], valid_range=None, valid_values=None,
            example_value=None, gotchas=[], nhl_api_equivalent=None,
            nhl_api_source_field="x", deprecated_in_year=None,
        )


def test_columnspec_rejects_unknown_mode():
    with pytest.raises(ValueError, match="invalid mode"):
        ColumnSpec(
            name="x", type="INT64", mode="MAYBE",  # type: ignore[arg-type]
            short_description="x", business_definition="x",
            semantic_tags=[], valid_range=None, valid_values=None,
            example_value=None, gotchas=[], nhl_api_equivalent=None,
            nhl_api_source_field="x", deprecated_in_year=None,
        )


def test_columnspec_accepts_repeated_mode():
    spec = ColumnSpec(
        name="ids", type="INT64", mode="REPEATED",
        short_description="x", business_definition="x",
        semantic_tags=[], valid_range=None, valid_values=None,
        example_value=None, gotchas=[], nhl_api_equivalent=None,
        nhl_api_source_field="x", deprecated_in_year=None,
    )
    assert spec.mode == "REPEATED"


def test_partitioning_spec_construction():
    p = PartitioningSpec(field="game_date", type="DAY", clustering=["season", "game_type"])
    assert p.field == "game_date"
    assert p.clustering == ["season", "game_type"]
