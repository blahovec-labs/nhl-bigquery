"""CLI entrypoint: nhl-bigquery {sync, docs, verify}.

The sync command implements the lockstep chunked pipeline:
  for each chunk:
    fetch /score/{date} for every date in chunk
    for each game_id seen in the chunk:
      fetch play-by-play, shift-charts, boxscore, right-rail, landing
      transform → plays, officials, boxscore, shifts DataFrames
    for each date in chunk: fetch /standings/{date}
    write all six tables; record chunk success
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date as _date
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

from nhl_bigquery._version import __version__
from nhl_bigquery.boxscore.schema import BOXSCORE_SCHEMA
from nhl_bigquery.boxscore.schema import get_partitioning as boxscore_partitioning
from nhl_bigquery.boxscore.transform import transform_boxscore_to_df
from nhl_bigquery.client import NHLAPIClient
from nhl_bigquery.games.schema import GAMES_SCHEMA
from nhl_bigquery.games.schema import get_partitioning as games_partitioning
from nhl_bigquery.games.transform import (
    transform_landing_to_games_row,
    transform_score_to_games_rows,
)
from nhl_bigquery.officials.schema import OFFICIALS_SCHEMA
from nhl_bigquery.officials.schema import get_partitioning as officials_partitioning
from nhl_bigquery.officials.transform import transform_right_rail_to_officials_df
from nhl_bigquery.plays.schema import PLAYS_SCHEMA
from nhl_bigquery.plays.schema import get_partitioning as plays_partitioning
from nhl_bigquery.plays.transform import transform_game_to_plays_df
from nhl_bigquery.runs import RunsTable, RunsTableRef, iter_chunks
from nhl_bigquery.schema import ColumnSpec
from nhl_bigquery.shifts.schema import SHIFTS_SCHEMA
from nhl_bigquery.shifts.schema import get_partitioning as shifts_partitioning
from nhl_bigquery.shifts.transform import transform_shift_charts_to_df
from nhl_bigquery.standings.schema import STANDINGS_SCHEMA
from nhl_bigquery.standings.schema import get_partitioning as standings_partitioning
from nhl_bigquery.standings.transform import transform_standings_to_df
from nhl_bigquery.writer import BigQueryWriter, TableRef

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("nhl-bigquery")


def _to_bq_schema(specs: list[ColumnSpec]) -> list[bigquery.SchemaField]:
    """Convert a list of ColumnSpec objects to BigQuery SchemaField list."""
    return [
        bigquery.SchemaField(name=s.name, field_type=s.type, mode=s.mode)
        for s in specs
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nhl-bigquery")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    # sync
    p = sub.add_parser("sync", help="Pull from NHL API and write to BigQuery")
    p.add_argument("--start", required=True, help="YYYY-MM-DD start (inclusive)")
    p.add_argument("--end", required=True, help="YYYY-MM-DD end (inclusive)")
    p.add_argument("--plays-table", required=True,
                   help="project.dataset.table for nhl_plays")
    p.add_argument("--games-table")
    p.add_argument("--officials-table")
    p.add_argument("--boxscore-table")
    p.add_argument("--shifts-table")
    p.add_argument("--standings-table")
    p.add_argument("--runs-table")
    p.add_argument("--skip-games", action="store_true")
    p.add_argument("--skip-officials", action="store_true")
    p.add_argument("--skip-boxscore", action="store_true")
    p.add_argument("--skip-shifts", action="store_true")
    p.add_argument("--skip-standings", action="store_true")
    p.add_argument("--chunk-by", default="month", choices=["year", "month", "range"])
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--sleep-seconds", type=float, default=1.0,
                   help="API politeness sleep in seconds (default 1.0; "
                        "lower = faster backfill but higher 429 risk).")

    # docs (filled in Task 23)
    p_docs = sub.add_parser("docs", help="Render documentation in various formats")
    p_docs.add_argument("--format", required=True,
                        choices=["bq-apply", "llm", "dictionary", "markdown", "dbt"])
    p_docs.add_argument("--table")
    p_docs.add_argument("--dataset")
    p_docs.add_argument("--output", default="-")
    p_docs.add_argument("--apply", action="store_true")
    p_docs.add_argument("--dictionary-table")

    # verify (filled in Task 25)
    p_v = sub.add_parser("verify", help="Compare aggregations to authoritative sources")
    p_v.add_argument("--source", default="internal",
                     choices=["nhl-api", "internal"])
    p_v.add_argument("--aggregation", required=True,
                     choices=["player-season", "team-season", "game-boxscore",
                              "internal-consistency"])
    p_v.add_argument("--metric", default="all")
    p_v.add_argument("--season", type=int)
    p_v.add_argument("--table", required=True)
    p_v.add_argument("--tolerance", type=float)
    p_v.add_argument("--min-sample-size", type=int, default=50)
    p_v.add_argument("--threshold", type=float, default=0.99)
    p_v.add_argument("--output", default="-")

    return parser


def _default_ref(plays_table: str, suffix: str) -> str:
    base = TableRef.parse(plays_table)
    return f"{base.project}.{base.dataset}.{suffix}"


def cmd_sync(ns: argparse.Namespace) -> int:
    plays_ref = TableRef.parse(ns.plays_table)
    api = NHLAPIClient(sleep_seconds=ns.sleep_seconds)
    chunks = iter_chunks(ns.start, ns.end, ns.chunk_by)
    log.info("planned %d chunks (by %s)", len(chunks), ns.chunk_by)

    if ns.dry_run:
        for cs, ce in chunks:
            log.info("dry-run chunk %s -> %s", cs, ce)
        return 0

    bq = bigquery.Client()
    writer = BigQueryWriter(client=bq)
    runs = RunsTable(client=bq)
    runs_ref = RunsTableRef.parse(
        ns.runs_table or _default_ref(ns.plays_table, "_nhl_ingest_runs")
    )
    runs.create_table_if_missing(runs_ref)

    games_ref = (None if ns.skip_games
                 else TableRef.parse(ns.games_table or _default_ref(ns.plays_table, "games")))
    officials_ref = (None if ns.skip_officials
                     else TableRef.parse(
                         ns.officials_table or _default_ref(ns.plays_table, "game_officials")))
    boxscore_ref = (None if ns.skip_boxscore
                    else TableRef.parse(
                        ns.boxscore_table or _default_ref(ns.plays_table, "boxscore_stats")))
    shifts_ref = (None if ns.skip_shifts
                  else TableRef.parse(ns.shifts_table or _default_ref(ns.plays_table, "shifts")))
    standings_ref = (None if ns.skip_standings
                     else TableRef.parse(
                         ns.standings_table or _default_ref(ns.plays_table, "standings")))

    if ns.resume:
        completed = runs.completed_chunks(ref=runs_ref)
        before = len(chunks)
        chunks = [
            (cs, ce) for cs, ce in chunks
            if (_date.fromisoformat(cs), _date.fromisoformat(ce)) not in completed
        ]
        skipped = before - len(chunks)
        if skipped:
            log.info("--resume: skipping %d completed chunks", skipped)

    for cs, ce in chunks:
        log.info("chunk %s -> %s", cs, ce)
        cs_d = _date.fromisoformat(cs)
        ce_d = _date.fromisoformat(ce)
        try:
            plays_rows = []
            games_rows = []
            officials_rows = []
            boxscore_rows = []
            shifts_rows = []
            standings_rows = []

            # Step 1: fetch /score/{date} for every date in the chunk
            cur = cs_d
            game_ids_with_dates: list[tuple[int, str]] = []
            while cur <= ce_d:
                d = cur.isoformat()
                score = api.get_score(d)
                games_in_score = (score or {}).get("games") or []
                for g in games_in_score:
                    game_ids_with_dates.append((int(g["id"]), g.get("gameDate") or d))
                if games_ref is not None:
                    df_score = transform_score_to_games_rows(score, date=d)
                    if not df_score.empty:
                        games_rows.append(df_score)
                if standings_ref is not None:
                    st = api.get_standings(d)
                    df_st = transform_standings_to_df(st, snapshot_date=d)
                    if not df_st.empty:
                        standings_rows.append(df_st)
                cur += pd.Timedelta(days=1)

            # Step 2: fetch per-game data + transform
            seen_game_ids: set[int] = set()
            for game_id, game_date in game_ids_with_dates:
                if game_id in seen_game_ids:
                    continue
                seen_game_ids.add(game_id)
                pbp = api.get_play_by_play(game_id)
                shifts = api.get_shift_charts(game_id)
                bs = api.get_boxscore(game_id) if boxscore_ref is not None else None
                rr = api.get_right_rail(game_id) if officials_ref is not None else None
                landing = api.get_landing(game_id)

                plays_df = transform_game_to_plays_df(pbp=pbp, shift_charts=shifts,
                                                     landing=landing)
                if not plays_df.empty:
                    plays_rows.append(plays_df)

                if games_ref is not None:
                    landing_row = transform_landing_to_games_row(landing)
                    games_rows.append(pd.DataFrame([landing_row]))

                if officials_ref is not None and rr is not None:
                    officials_df = transform_right_rail_to_officials_df(
                        rr, game_id=game_id, game_date=game_date)
                    if not officials_df.empty:
                        officials_rows.append(officials_df)

                if boxscore_ref is not None and bs is not None:
                    boxscore_df = transform_boxscore_to_df(bs)
                    if not boxscore_df.empty:
                        boxscore_rows.append(boxscore_df)

                if shifts_ref is not None:
                    shifts_df = transform_shift_charts_to_df(shifts, game_date=game_date)
                    if not shifts_df.empty:
                        shifts_rows.append(shifts_df)

            # Step 3: ensure all tables exist before writing
            if plays_ref is not None:
                p = plays_partitioning()
                writer.create_table_if_missing(
                    plays_ref, _to_bq_schema(PLAYS_SCHEMA),
                    partition_field=p.field, clustering=p.clustering or None,
                )
            if games_ref is not None:
                p = games_partitioning()
                writer.create_table_if_missing(
                    games_ref, _to_bq_schema(GAMES_SCHEMA),
                    partition_field=p.field, clustering=p.clustering or None,
                )
            if officials_ref is not None:
                p = officials_partitioning()
                writer.create_table_if_missing(
                    officials_ref, _to_bq_schema(OFFICIALS_SCHEMA),
                    partition_field=p.field, clustering=p.clustering or None,
                )
            if boxscore_ref is not None:
                p = boxscore_partitioning()
                writer.create_table_if_missing(
                    boxscore_ref, _to_bq_schema(BOXSCORE_SCHEMA),
                    partition_field=p.field, clustering=p.clustering or None,
                )
            if shifts_ref is not None:
                p = shifts_partitioning()
                writer.create_table_if_missing(
                    shifts_ref, _to_bq_schema(SHIFTS_SCHEMA),
                    partition_field=p.field, clustering=p.clustering or None,
                )
            if standings_ref is not None:
                p = standings_partitioning()
                writer.create_table_if_missing(
                    standings_ref, _to_bq_schema(STANDINGS_SCHEMA),
                    partition_field=p.field, clustering=p.clustering or None,
                )

            # Step 4: write in deterministic order
            def _concat_and_write(table_ref: TableRef | None, dfs: list[pd.DataFrame],
                                  partition_field: str, kind: str) -> int:
                if table_ref is None or not dfs:
                    return 0
                df = pd.concat(dfs, ignore_index=True)
                # On games, dedupe by game_id (score + landing may both produce rows)
                if kind == "games":
                    df = df.drop_duplicates(subset=["game_id"], keep="last")
                return writer.write(table_ref, df, partition_field=partition_field,
                                    chunk_start=cs, chunk_end=ce)

            rows_written = {
                "games": _concat_and_write(games_ref, games_rows, "game_date", "games"),
                "officials": _concat_and_write(
                    officials_ref, officials_rows, "game_date", "officials"),
                "boxscore": _concat_and_write(boxscore_ref, boxscore_rows, "game_date", "boxscore"),
                "shifts": _concat_and_write(shifts_ref, shifts_rows, "game_date", "shifts"),
                "plays": _concat_and_write(plays_ref, plays_rows, "game_date", "plays"),
                "standings": _concat_and_write(
                    standings_ref, standings_rows, "snapshot_date", "standings"),
            }

            if sum(rows_written.values()) == 0:
                runs.record_empty(ref=runs_ref, chunk_start=cs_d, chunk_end=ce_d,
                                  chunk_kind=ns.chunk_by)
                log.info("no rows for chunk %s -> %s", cs, ce)
            else:
                runs.record_success(ref=runs_ref, chunk_start=cs_d, chunk_end=ce_d,
                                    chunk_kind=ns.chunk_by, rows_written=rows_written)

        except Exception as e:
            runs.record_failed(ref=runs_ref, chunk_start=cs_d, chunk_end=ce_d,
                               chunk_kind=ns.chunk_by, error=str(e))
            raise

    return 0


def cmd_docs(ns: argparse.Namespace) -> int:
    from nhl_bigquery.docs.renderers import (
        apply_data_dictionary,
        render_bq_descriptions,
        render_data_dictionary,
        render_dbt_yaml,
        render_llm_context,
        render_markdown,
    )
    from nhl_bigquery.docs.taxonomy import TABLES

    if ns.format == "bq-apply":
        if not ns.table:
            log.error("--table required for bq-apply")
            return 2
        ref = TableRef.parse(ns.table)
        client = bigquery.Client()
        table = client.get_table(str(ref))
        # Try direct match first, then suffix match
        kind = ref.table if ref.table in TABLES else None
        if kind is None:
            for k in TABLES:
                if ref.table.endswith(k) or ref.table == k:
                    kind = k
                    break
        if kind is None:
            log.error("could not infer table_kind from %s; expected suffix in %s",
                      ref.table, list(TABLES.keys()))
            return 2
        table.schema = render_bq_descriptions(table_kind=kind)
        client.update_table(table, ["schema"])
        log.info("updated descriptions on %s", ref)
        return 0

    if ns.format == "dictionary":
        if not (ns.dataset and ns.table):
            log.error("--dataset and --table required for dictionary")
            return 2
        ref = TableRef.parse(ns.table)
        if ns.apply:
            if not ns.dictionary_table:
                log.error("--dictionary-table required with --apply")
                return 2
            client = bigquery.Client()
            n = apply_data_dictionary(
                client=client, dictionary_table=ns.dictionary_table,
                dataset=ns.dataset, table=ref.table,
            )
            log.info("applied %d rows to %s", n, ns.dictionary_table)
            return 0
        out = json.dumps(render_data_dictionary(dataset=ns.dataset, table=ref.table),
                         indent=2)
    elif ns.format == "llm":
        out = render_llm_context()
    elif ns.format == "markdown":
        out = render_markdown()
    elif ns.format == "dbt":
        out = render_dbt_yaml()
    else:
        raise AssertionError(f"unhandled format {ns.format}")

    if ns.output == "-":
        sys.stdout.write(out)
    else:
        Path(ns.output).write_text(out, encoding="utf-8")
    return 0


def cmd_verify(ns: argparse.Namespace) -> int:
    from nhl_bigquery.verify.internal import run_internal_checks
    from nhl_bigquery.verify.nhl_api import (
        verify_game_boxscore,
        verify_player_season,
        verify_team_season,
    )

    client = bigquery.Client()
    api = NHLAPIClient()
    table = ns.table
    base = TableRef.parse(table)

    if ns.source == "internal":
        result = run_internal_checks(
            client=client,
            plays_table=table,
            shifts_table=f"{base.project}.{base.dataset}.shifts",
            games_table=f"{base.project}.{base.dataset}.games",
        )
    elif ns.source == "nhl-api":
        if ns.aggregation == "team-season":
            result = verify_team_season(
                client=client, api=api, table=table, season=ns.season
            )
        elif ns.aggregation == "player-season":
            result = verify_player_season(
                client=client, api=api, table=table, season=ns.season,
                min_sample_size=ns.min_sample_size,
                tolerance=int(ns.tolerance or 0),
            )
        elif ns.aggregation == "game-boxscore":
            # Convention: --season carries game_id for this aggregation.
            result = verify_game_boxscore(
                client=client, api=api, table=table, game_id=ns.season
            )
        else:
            raise AssertionError(f"unsupported aggregation {ns.aggregation}")
    else:
        raise AssertionError(f"unsupported source {ns.source}")

    print(result.summary())
    return 0 if result.overall_pass else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    if ns.command == "sync":
        return cmd_sync(ns)
    if ns.command == "docs":
        return cmd_docs(ns)
    if ns.command == "verify":
        return cmd_verify(ns)
    raise AssertionError(f"unhandled command {ns.command}")


if __name__ == "__main__":
    sys.exit(main())
