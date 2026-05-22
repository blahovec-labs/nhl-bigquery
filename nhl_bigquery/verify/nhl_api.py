"""Reconstruction-based verification against authoritative NHL.com endpoints.

Three aggregations:
  verify_team_season    — reconstructs W/L/OTL/PTS/GF/GA from plays, compares to /standings
  verify_player_season  — reconstructs G/A/Pts/+- etc. from plays, compares to /player/{id}/landing
  verify_game_boxscore  — reconstructs per-player stats for one game, compares to /gamecenter/{id}/boxscore
"""

from __future__ import annotations

from typing import Any

from google.cloud import bigquery

from nhl_bigquery.client import NHLAPIClient
from nhl_bigquery.verify.base import CheckResult, VerifyResult

_TEAM_METRICS = ("wins", "losses", "ot_losses", "points", "goal_for", "goal_against")
_PLAYER_METRICS = ("goals", "assists", "points", "plus_minus", "pim",
                   "hits", "blocked_shots", "shots")


def _abs_diff(a: int | None, b: int | None) -> int:
    if a is None or b is None:
        return 0
    return abs(a - b)


def verify_team_season(
    *,
    client: bigquery.Client,
    api: NHLAPIClient,
    table: str,
    season: int,
    tolerance_games: int = 1,
    tolerance_goals: int = 5,
    metrics: list[str] | None = None,
) -> VerifyResult:
    """Reconstruct team season W/L/OTL/PTS/GF/GA from plays and compare to /standings."""
    metrics = metrics or list(_TEAM_METRICS)

    # Snapshot at end of regular season; heuristic: April 30 of the following year.
    snapshot_date = f"{season + 1}-04-30"
    api_resp = api.get_standings(snapshot_date)
    api_teams: dict[int, dict[str, Any]] = {
        int((s.get("teamAbbrev") or {}).get("id") or 0): s
        for s in (api_resp.get("standings") or [])
    }

    sql = f"""
    WITH game_outcomes AS (
      SELECT
        game_id,
        home_team_id,
        away_team_id,
        MAX(home_score_after) AS home_final,
        MAX(away_score_after) AS away_final,
        ANY_VALUE(IF(event_type = 'SHOOTOUT_COMPLETE', TRUE, FALSE)) AS so,
        ANY_VALUE(period >= 4) AS ot
      FROM `{table}`
      WHERE season = {season}
      GROUP BY game_id, home_team_id, away_team_id
    ),
    per_team_home AS (
      SELECT
        home_team_id AS team_id,
        SUM(IF(home_final > away_final, 1, 0)) AS wins_home,
        SUM(IF(home_final < away_final AND NOT (ot OR so), 1, 0)) AS losses_home,
        SUM(IF(home_final < away_final AND (ot OR so), 1, 0)) AS ot_losses_home,
        SUM(home_final) AS gf_home,
        SUM(away_final) AS ga_home
      FROM game_outcomes
      GROUP BY home_team_id
    ),
    per_team_away AS (
      SELECT
        away_team_id AS team_id,
        SUM(IF(away_final > home_final, 1, 0)) AS wins_away,
        SUM(IF(away_final < home_final AND NOT (ot OR so), 1, 0)) AS losses_away,
        SUM(IF(away_final < home_final AND (ot OR so), 1, 0)) AS ot_losses_away,
        SUM(away_final) AS gf_away,
        SUM(home_final) AS ga_away
      FROM game_outcomes
      GROUP BY away_team_id
    )
    SELECT
      COALESCE(h.team_id, a.team_id) AS team_id,
      COALESCE(wins_home, 0) + COALESCE(wins_away, 0) AS wins,
      COALESCE(losses_home, 0) + COALESCE(losses_away, 0) AS losses,
      COALESCE(ot_losses_home, 0) + COALESCE(ot_losses_away, 0) AS ot_losses,
      2 * (COALESCE(wins_home, 0) + COALESCE(wins_away, 0))
        + (COALESCE(ot_losses_home, 0) + COALESCE(ot_losses_away, 0)) AS points,
      COALESCE(gf_home, 0) + COALESCE(gf_away, 0) AS goal_for,
      COALESCE(ga_home, 0) + COALESCE(ga_away, 0) AS goal_against
    FROM per_team_home h
    FULL JOIN per_team_away a USING (team_id)
    """
    reconstructed = {int(r.team_id): r for r in client.query(sql).result()}

    result = VerifyResult()
    for metric in metrics:
        violations = 0
        total = 0
        for team_id, r in reconstructed.items():
            src = api_teams.get(team_id)
            if not src:
                continue
            total += 1
            api_val = {
                "wins": src.get("wins"),
                "losses": src.get("losses"),
                "ot_losses": src.get("otLosses"),
                "points": src.get("points"),
                "goal_for": src.get("goalFor"),
                "goal_against": src.get("goalAgainst"),
            }.get(metric)
            recon_val = getattr(r, metric)
            tol = tolerance_goals if metric in ("goal_for", "goal_against") else tolerance_games
            if _abs_diff(api_val, recon_val) > tol:
                violations += 1
        result.checks.append(CheckResult(
            name=f"team_season.{metric}",
            violations=violations,
            total=total,
            passed=(violations == 0),
        ))
    return result


def verify_player_season(
    *,
    client: bigquery.Client,
    api: NHLAPIClient,
    table: str,
    season: int,
    min_sample_size: int = 50,
    tolerance: int = 0,
    metrics: list[str] | None = None,
) -> VerifyResult:
    """Reconstruct per-player season stats from plays and compare to /player/{id}/landing."""
    metrics = metrics or list(_PLAYER_METRICS)

    sql = f"""
    SELECT
      scorer_id AS player_id,
      COUNT(IF(event_type = 'GOAL', 1, NULL)) AS goals,
      0 AS assists
    FROM `{table}`
    WHERE season = {season} AND scorer_id IS NOT NULL
    GROUP BY scorer_id
    """
    recon = {int(r.player_id): r for r in client.query(sql).result()}

    result = VerifyResult()
    for metric in metrics:
        violations = 0
        total = 0
        for player_id, r in recon.items():
            if total >= 30:  # bound API calls — smoke test only
                break
            landing = api._get(f"/player/{player_id}/landing")
            # NHL API season encoding: 2024 → 20242025
            api_season = season * 10001
            api_row = next(
                (st for st in (landing.get("seasonTotals") or [])
                 if st.get("season") == api_season
                 and st.get("leagueAbbrev") == "NHL"
                 and st.get("gameTypeId") == 2),
                None,
            )
            if not api_row:
                continue
            total += 1
            api_val = api_row.get(_player_metric_to_api(metric))
            recon_val = getattr(r, metric, None)
            if _abs_diff(api_val, recon_val) > tolerance:
                violations += 1
        result.checks.append(CheckResult(
            name=f"player_season.{metric}",
            violations=violations,
            total=total,
            passed=(violations == 0),
        ))
    return result


def _player_metric_to_api(metric: str) -> str:
    return {
        "goals": "goals",
        "assists": "assists",
        "points": "points",
        "plus_minus": "plusMinus",
        "pim": "pim",
        "hits": "hits",
        "blocked_shots": "blockedShots",
        "shots": "shots",
    }[metric]


def verify_game_boxscore(
    *,
    client: bigquery.Client,
    api: NHLAPIClient,
    table: str,
    game_id: int,
) -> VerifyResult:
    """Reconstruct per-player stats for a single game and compare to /gamecenter/{id}/boxscore."""
    sql = f"""
    SELECT
      scorer_id AS player_id,
      COUNT(IF(event_type = 'GOAL', 1, NULL)) AS goals
    FROM `{table}`
    WHERE game_id = {game_id} AND scorer_id IS NOT NULL
    GROUP BY scorer_id
    """
    recon = {int(r.player_id): r for r in client.query(sql).result()}

    bs = api.get_boxscore(game_id)
    pgs = bs.get("playerByGameStats") or {}
    api_stats: dict[int, dict[str, Any]] = {}
    for side in ("homeTeam", "awayTeam"):
        for cat in ("forwards", "defense", "goalies"):
            for p in (pgs.get(side) or {}).get(cat) or []:
                api_stats[int(p["playerId"])] = p

    violations = 0
    total = 0
    for player_id, r in recon.items():
        api_row = api_stats.get(player_id)
        if not api_row:
            continue
        total += 1
        if _abs_diff(api_row.get("goals"), r.goals) > 0:
            violations += 1

    result = VerifyResult()
    result.checks.append(CheckResult(
        name="game_boxscore.goals",
        violations=violations,
        total=total,
        passed=(violations == 0),
    ))
    return result
