# Changelog

## 0.1.1

- **`cmd_sync` is resilient to per-game failures.** A single bad game (API 500s, malformed payload, etc.) now logs a warning and is skipped rather than crashing the entire chunk. A summary line is logged at the end of each chunk if any games were skipped.
- **Preseason games are excluded by default.** Games with `gameType=1` are filtered out in `cmd_sync` because the NHL API is unreliable for preseason landing/PBP endpoints and preseason data is not useful for analytics. Use `--include-preseason` to opt back in.

## 0.1.0

Initial release.

- `sync` command writes six tables in lockstep chunks: nhl_plays (with on-ice arrays merged from shift-charts), games, game_officials, boxscore_stats, shifts, standings
- `--resume` support via `_nhl_ingest_runs` log
- 5 doc renderers (bq-apply / llm / dictionary / markdown / dbt) backed by ColumnSpec SSoT
- `verify --source internal` runs 8 zero-tolerance consistency checks
- `verify --source nhl-api` reconstructs and compares team-season / player-season / game-boxscore against authoritative endpoints
- Backfill from 2010-11 onward (coordinate era)
