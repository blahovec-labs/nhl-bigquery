# nhl-bigquery

Idempotent NHL play-by-play (with on-ice arrays) → BigQuery ingestion, with first-class documentation for SQL/LLM agents and round-trip validation against the NHL public API.

## Install

    pip install nhl-bigquery

## Quickstart

    gcloud auth application-default login
    nhl-bigquery sync \
        --start 2024-10-01 --end 2025-06-30 \
        --plays-table myproject.mydataset.nhl_plays

## Documentation

    nhl-bigquery docs --format llm > NHL_FOR_LLMS.md

## Verification

    nhl-bigquery verify \
        --source nhl-api \
        --aggregation team-season \
        --metric all --season 2024 \
        --table myproject.mydataset.nhl_plays

MIT licensed. This software does not include or distribute NHL data.
