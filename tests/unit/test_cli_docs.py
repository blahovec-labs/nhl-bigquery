from io import StringIO
from unittest.mock import patch

from nhl_bigquery.cli import main


def test_docs_llm_to_stdout(capsys):
    main(["docs", "--format", "llm"])
    captured = capsys.readouterr()
    assert "nhl_plays" in captured.out
    assert "games" in captured.out


def test_docs_markdown_to_file(tmp_path):
    out = tmp_path / "doc.md"
    main(["docs", "--format", "markdown", "--output", str(out)])
    text = out.read_text(encoding="utf-8")
    assert "Column Reference" in text


def test_docs_dbt_to_stdout(capsys):
    main(["docs", "--format", "dbt"])
    captured = capsys.readouterr()
    assert captured.out.startswith("version: 2")
