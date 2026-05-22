# nhl-bigquery

Idempotent NHL play-by-play (with on-ice arrays merged from shift-charts) → BigQuery ingestion, with first-class documentation for SQL/LLM agents and verification against the NHL public API.

## Install

    pip install nhl-bigquery

## Quickstart

    gcloud auth application-default login
    nhl-bigquery sync \
        --start 2024-10-01 --end 2025-06-30 \
        --plays-table myproject.mydataset.nhl_plays

This writes six tables to `myproject.mydataset.*`:

- `nhl_plays` — one row per event, with `home_on_ice_ids` / `away_on_ice_ids` arrays
- `games` — schedule dimension
- `game_officials` — referees + linesmen per game
- `boxscore_stats` — per-player per-game stats
- `shifts` — per-shift per-player intervals
- `standings` — daily team-standings snapshots

## Backfill

Backfill 15 seasons in resumable monthly chunks:

    nhl-bigquery sync \
        --start 2010-10-01 --end 2026-05-11 \
        --chunk-by month --resume \
        --plays-table myproject.mydataset.nhl_plays

`--resume` skips chunks already recorded as `success` or `empty` in
`<dataset>._nhl_ingest_runs`. Re-running with the same `--chunk-by` is
safe; switching between runs will re-process (chunks must match exactly).

## Documentation

    nhl-bigquery docs --format llm > NHL_FOR_LLMS.md
    nhl-bigquery docs --format bq-apply --table myproject.mydataset.nhl_plays

Five formats: `bq-apply` (push descriptions to BigQuery), `llm` (one
Markdown file packing every column for LLM context), `dictionary`
(JSON rows for a data dictionary table), `markdown` (human reference),
and `dbt` (dbt YAML schema stub).

## Verification

    nhl-bigquery verify --source internal \
        --aggregation internal-consistency \
        --table myproject.mydataset.nhl_plays

    nhl-bigquery verify --source nhl-api \
        --aggregation team-season --metric all --season 2024 \
        --table myproject.mydataset.nhl_plays

MIT licensed. This software does not include or distribute NHL data.
