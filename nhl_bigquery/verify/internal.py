"""Internal-consistency checks. Zero-tolerance: any violation fraction > 0 fails."""

from __future__ import annotations

from typing import Callable

from google.cloud import bigquery

from nhl_bigquery.verify.base import CheckResult, VerifyResult


def _q(client: bigquery.Client, sql: str) -> tuple[int, int]:
    """Run an SQL that returns (violations, total) and return as ints."""
    rows = list(client.query(sql).result())
    if not rows:
        return (0, 0)
    r = rows[0]
    return (int(getattr(r, "violations", 0)), int(getattr(r, "total", 0)))


def _check_on_ice_skater_count_valid(client, *, plays_table, **kw) -> tuple[int, int]:
    sql = f"""
    SELECT
      SUM(IF(ARRAY_LENGTH(home_on_ice_ids) NOT BETWEEN 3 AND 6
             OR ARRAY_LENGTH(away_on_ice_ids) NOT BETWEEN 3 AND 6, 1, 0)) AS violations,
      COUNT(*) AS total
    FROM `{plays_table}`
    WHERE period_type != 'SO' AND source_quality = 'FULL'
    """
    return _q(client, sql)


def _check_no_orphan_event_player(client, *, plays_table, **kw) -> tuple[int, int]:
    # An event_player_id should be on-ice for the event_owner's side
    sql = f"""
    WITH events AS (
      SELECT *,
        CASE WHEN event_owner_team_id = home_team_id THEN home_on_ice_ids ELSE away_on_ice_ids END
        AS team_on_ice
      FROM `{plays_table}`
      WHERE source_quality = 'FULL' AND period_type != 'SO'
        AND event_owner_team_id IS NOT NULL
    )
    SELECT
      SUM(IF(shooter_id IS NOT NULL AND shooter_id NOT IN UNNEST(team_on_ice), 1, 0)) AS violations,
      COUNT(*) AS total
    FROM events
    """
    return _q(client, sql)


def _check_score_monotonic(client, *, plays_table, **kw) -> tuple[int, int]:
    sql = f"""
    SELECT
      SUM(IF(home_score_after < home_score_before OR away_score_after < away_score_before, 1, 0)) AS violations,
      COUNT(*) AS total
    FROM `{plays_table}`
    WHERE home_score_before IS NOT NULL AND home_score_after IS NOT NULL
    """
    return _q(client, sql)


def _check_period_time_in_bounds(client, *, plays_table, **kw) -> tuple[int, int]:
    sql = f"""
    SELECT
      SUM(IF(time_in_period IS NOT NULL
             AND SAFE_CAST(SPLIT(time_in_period, ':')[OFFSET(0)] AS INT64) > 20, 1, 0)) AS violations,
      COUNT(*) AS total
    FROM `{plays_table}`
    """
    return _q(client, sql)


def _check_coords_in_bounds_or_null(client, *, plays_table, **kw) -> tuple[int, int]:
    sql = f"""
    SELECT
      SUM(IF(NOT (
        (x_coord BETWEEN -100 AND 100 AND y_coord BETWEEN -42.5 AND 42.5)
        OR (x_coord IS NULL AND y_coord IS NULL)
      ), 1, 0)) AS violations,
      COUNT(*) AS total
    FROM `{plays_table}`
    """
    return _q(client, sql)


def _check_no_duplicate_events(client, *, plays_table, **kw) -> tuple[int, int]:
    sql = f"""
    WITH dupes AS (
      SELECT game_id, event_id, COUNT(*) AS n
      FROM `{plays_table}`
      GROUP BY game_id, event_id
      HAVING COUNT(*) > 1
    )
    SELECT
      (SELECT COUNT(*) FROM dupes) AS violations,
      (SELECT COUNT(*) FROM `{plays_table}`) AS total
    """
    return _q(client, sql)


def _check_no_future_games(client, *, games_table, **kw) -> tuple[int, int]:
    sql = f"""
    SELECT
      SUM(IF(game_date > CURRENT_DATE(), 1, 0)) AS violations,
      COUNT(*) AS total
    FROM `{games_table}`
    WHERE game_state IN ('FINAL', 'OFF')
    """
    return _q(client, sql)


def _check_shifts_valid_intervals(client, *, shifts_table, **kw) -> tuple[int, int]:
    sql = f"""
    SELECT
      SUM(IF(start_abs_seconds >= end_abs_seconds, 1, 0)) AS violations,
      COUNT(*) AS total
    FROM `{shifts_table}`
    """
    return _q(client, sql)


INTERNAL_CHECKS: dict[str, Callable] = {
    "on_ice_skater_count_valid": _check_on_ice_skater_count_valid,
    "no_orphan_event_player": _check_no_orphan_event_player,
    "score_monotonic": _check_score_monotonic,
    "period_time_in_bounds": _check_period_time_in_bounds,
    "coords_in_bounds_or_null": _check_coords_in_bounds_or_null,
    "no_duplicate_events": _check_no_duplicate_events,
    "no_future_games": _check_no_future_games,
    "shifts_valid_intervals": _check_shifts_valid_intervals,
}


def run_internal_checks(*, client: bigquery.Client,
                        plays_table: str, shifts_table: str,
                        games_table: str) -> VerifyResult:
    result = VerifyResult()
    for name, fn in INTERNAL_CHECKS.items():
        violations, total = fn(client,
                               plays_table=plays_table,
                               shifts_table=shifts_table,
                               games_table=games_table)
        result.checks.append(CheckResult(
            name=name, violations=violations, total=total,
            passed=(violations == 0),
        ))
    return result
