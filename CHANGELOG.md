# Changelog

## 0.1.0

Initial release.

- `sync` command writes six tables in lockstep chunks: nhl_plays (with on-ice arrays merged from shift-charts), games, game_officials, boxscore_stats, shifts, standings
- `--resume` support via `_nhl_ingest_runs` log
- 5 doc renderers (bq-apply / llm / dictionary / markdown / dbt) backed by ColumnSpec SSoT
- `verify --source internal` runs 8 zero-tolerance consistency checks
- `verify --source nhl-api` reconstructs and compares team-season / player-season / game-boxscore against authoritative endpoints
- Backfill from 2010-11 onward (coordinate era)
