from datetime import datetime

from nhl_bigquery.docs.renderers import (
    render_bq_descriptions, render_data_dictionary, render_dbt_yaml,
    render_llm_context, render_markdown,
)


def test_render_llm_context_includes_every_table():
    out = render_llm_context()
    for tbl in ("nhl_plays", "games", "game_officials",
                "boxscore_stats", "shifts", "standings"):
        assert tbl in out, f"missing table reference {tbl} in LLM context"


def test_render_markdown_is_non_empty():
    assert len(render_markdown().strip()) > 100


def test_render_dbt_yaml_starts_with_version():
    out = render_dbt_yaml()
    assert out.startswith("version: 2")


def test_render_bq_descriptions_returns_schema_fields():
    fields = render_bq_descriptions(table_kind="plays")
    assert len(fields) > 0
    for f in fields:
        assert hasattr(f, "name") and hasattr(f, "description")


def test_render_data_dictionary_rows():
    rows = render_data_dictionary(dataset="mydataset", table="nhl_plays")
    assert len(rows) > 0
    for r in rows:
        assert "dataset" in r and "column" in r and "business_definition" in r
