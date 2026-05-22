# Contributing

Bug reports and PRs welcome at https://github.com/blahovec-labs/nhl-bigquery.

## Dev setup

    pip install -e ".[dev]"
    pytest -q

## Capturing test fixtures

    python scripts/capture_fixture.py --game-id 2024020001 --out tests/fixtures/games/
