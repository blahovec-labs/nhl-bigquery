"""Unit tests for the CLI verify subcommand parser."""

from nhl_bigquery.cli import build_parser


def test_verify_parser():
    parser = build_parser()
    ns = parser.parse_args([
        "verify", "--source", "internal",
        "--aggregation", "internal-consistency",
        "--table", "p.d.nhl_plays",
    ])
    assert ns.source == "internal"
    assert ns.aggregation == "internal-consistency"
