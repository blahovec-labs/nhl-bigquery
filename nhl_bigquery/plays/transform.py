"""Transform raw NHL API JSON for one game into a plays DataFrame.

Inputs:
  pbp           - /gamecenter/{id}/play-by-play response
  shift_charts  - /gamecenter/{id}/shift-charts response
  landing       - /gamecenter/{id}/landing response (for game-level fields)

Output: pandas DataFrame with rows aligned to PLAYS_SCHEMA columns.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from nhl_bigquery.plays.merge import build_on_ice_at_event, parse_shifts
from nhl_bigquery.plays.strength import derive_strength_state
from nhl_bigquery.time_utils import event_abs_seconds

_GAME_TYPE_MAP = {1: "PR", 2: "R", 3: "P", 4: "AS"}

_EVENT_TYPE_MAP = {
    "goal": "GOAL",
    "shot-on-goal": "SHOT",
    "missed-shot": "MISSED_SHOT",
    "blocked-shot": "BLOCKED_SHOT",
    "hit": "HIT",
    "faceoff": "FACEOFF",
    "giveaway": "GIVEAWAY",
    "takeaway": "TAKEAWAY",
    "penalty": "PENALTY",
    "stoppage": "STOPPAGE",
    "period-start": "PERIOD_START",
    "period-end": "PERIOD_END",
    "game-end": "GAME_END",
    "shootout-complete": "SHOOTOUT_COMPLETE",
    "delayed-penalty": "DELAYED_PENALTY",
}

_PENALTY_SEVERITY_MAP = {
    "MIN": "MIN", "MAJ": "MAJ", "MIS": "MIS", "BEN": "BEN",
    "MAT": "MAT", "GAM": "GAM", "PS": "PS",
}


def _decode_situation_code(sc: str | None) -> tuple[int | None, int | None, bool | None, bool | None]:
    """Decode '1551' → (away_skaters, home_skaters, away_goalie, home_goalie)."""
    if not sc or len(sc) != 4 or not sc.isdigit():
        return (None, None, None, None)
    away_goalie = sc[0] == "1"
    away_skaters = int(sc[1])
    home_skaters = int(sc[2])
    home_goalie = sc[3] == "1"
    return (away_skaters, home_skaters, away_goalie, home_goalie)


def _zone_descriptor(code: str | None) -> str | None:
    return {"O": "offensive", "D": "defensive", "N": "neutral"}.get(code or "")


def _empty_row() -> dict[str, Any]:
    # Default-NULL row that downstream code fills selectively.
    return {
        "game_id": None, "event_id": None, "sort_order": None,
        "season": None, "game_date": None, "game_type": None,
        "period": None, "period_type": None, "time_in_period": None,
        "time_remaining": None, "event_abs_seconds": None,
        "event_type": None, "event_type_desc": None, "situation_code": None,
        "x_coord": None, "y_coord": None, "zone_code": None,
        "zone_descriptor": None, "event_owner_team_id": None,
        "shooter_id": None, "goalie_id": None, "scorer_id": None,
        "primary_assist_id": None, "secondary_assist_id": None,
        "hitter_id": None, "hittee_id": None,
        "winning_player_id": None, "losing_player_id": None,
        "drawn_by_id": None, "served_by_id": None,
        "penalty_player_id": None, "blocker_id": None,
        "committed_by_id": None,
        "shot_type": None, "penalty_minutes": None,
        "penalty_severity": None, "penalty_type_code": None,
        "penalty_type_desc": None,
        "home_score_before": None, "away_score_before": None,
        "home_score_after": None, "away_score_after": None,
        "home_team_id": None, "away_team_id": None,
        "home_team_abbrev": None, "away_team_abbrev": None,
        "home_on_ice_ids": [], "away_on_ice_ids": [],
        "home_skaters_on_ice": None, "away_skaters_on_ice": None,
        "home_goalie_on_ice": None, "away_goalie_on_ice": None,
        "strength_state": None,
        "source_quality": "FULL",
        "ingested_at": None,
    }


def transform_game_to_plays_df(
    *, pbp: dict[str, Any], shift_charts: dict[str, Any], landing: dict[str, Any]
) -> pd.DataFrame:
    """Transform one game's API responses into a plays DataFrame."""
    game_id = int(pbp.get("id") or landing.get("id"))
    game_date = pbp.get("gameDate") or landing.get("gameDate")
    season_raw = int(pbp.get("season") or landing.get("season"))
    season = season_raw // 10000  # 20242025 → 2024
    game_type_int = int(pbp.get("gameType") or landing.get("gameType"))
    game_type = _GAME_TYPE_MAP.get(game_type_int)
    home_team = pbp.get("homeTeam") or landing.get("homeTeam") or {}
    away_team = pbp.get("awayTeam") or landing.get("awayTeam") or {}
    home_team_id = int(home_team.get("id"))
    away_team_id = int(away_team.get("id"))
    home_abbrev = home_team.get("abbrev")
    away_abbrev = away_team.get("abbrev")

    # Parse shifts once for the entire game
    raw_shifts = (shift_charts or {}).get("data") or []
    parsed_shifts = parse_shifts(raw_shifts)
    has_shifts = bool(parsed_shifts)

    ingested_at = datetime.now(timezone.utc)

    # Track score state running totals (the API gives post-event scores
    # in details.homeScore/details.awayScore; we derive pre-event by
    # decrementing for own-team GOAL events).
    rows: list[dict[str, Any]] = []
    prev_home_score = 0
    prev_away_score = 0

    plays = (pbp or {}).get("plays") or []
    for play in plays:
        row = _empty_row()
        row["game_id"] = game_id
        row["game_date"] = game_date
        row["season"] = season
        row["game_type"] = game_type
        row["home_team_id"] = home_team_id
        row["away_team_id"] = away_team_id
        row["home_team_abbrev"] = home_abbrev
        row["away_team_abbrev"] = away_abbrev
        row["ingested_at"] = ingested_at

        row["event_id"] = play.get("eventId")
        row["sort_order"] = play.get("sortOrder")
        type_desc_key = play.get("typeDescKey")
        row["event_type_desc"] = type_desc_key
        row["event_type"] = _EVENT_TYPE_MAP.get(type_desc_key)

        period_desc = play.get("periodDescriptor") or {}
        row["period"] = period_desc.get("number")
        row["period_type"] = period_desc.get("periodType")
        row["time_in_period"] = play.get("timeInPeriod")
        row["time_remaining"] = play.get("timeRemaining")
        row["event_abs_seconds"] = (
            event_abs_seconds(row["period"], row["time_in_period"])
            if row["period"] is not None else None
        )

        row["situation_code"] = play.get("situationCode")

        details = play.get("details") or {}
        row["x_coord"] = details.get("xCoord")
        row["y_coord"] = details.get("yCoord")
        row["zone_code"] = details.get("zoneCode")
        row["zone_descriptor"] = _zone_descriptor(details.get("zoneCode"))

        row["event_owner_team_id"] = details.get("eventOwnerTeamId")
        row["shooter_id"] = details.get("shootingPlayerId")
        row["goalie_id"] = details.get("goalieInNetId")
        row["scorer_id"] = details.get("scoringPlayerId")
        row["primary_assist_id"] = details.get("assist1PlayerId")
        row["secondary_assist_id"] = details.get("assist2PlayerId")
        row["hitter_id"] = details.get("hittingPlayerId")
        row["hittee_id"] = details.get("hitteePlayerId")
        row["winning_player_id"] = details.get("winningPlayerId")
        row["losing_player_id"] = details.get("losingPlayerId")
        row["drawn_by_id"] = details.get("drawnByPlayerId")
        row["served_by_id"] = details.get("servedByPlayerId")
        row["penalty_player_id"] = details.get("committedByPlayerId")
        row["blocker_id"] = details.get("blockingPlayerId")
        # GIVEAWAY/TAKEAWAY use a generic playerId
        if row["event_type"] in ("GIVEAWAY", "TAKEAWAY"):
            row["committed_by_id"] = details.get("playerId")

        row["shot_type"] = details.get("shotType")
        row["penalty_minutes"] = details.get("duration")
        row["penalty_type_code"] = details.get("typeCode")
        row["penalty_severity"] = _PENALTY_SEVERITY_MAP.get(details.get("typeCode") or "")
        row["penalty_type_desc"] = details.get("descKey")

        # Score state: NHL API gives post-event scores
        home_score_after = details.get("homeScore")
        away_score_after = details.get("awayScore")
        row["home_score_after"] = home_score_after if home_score_after is not None else prev_home_score
        row["away_score_after"] = away_score_after if away_score_after is not None else prev_away_score
        row["home_score_before"] = prev_home_score
        row["away_score_before"] = prev_away_score
        prev_home_score = row["home_score_after"] or prev_home_score
        prev_away_score = row["away_score_after"] or prev_away_score

        # On-ice arrays + strength state
        on_ice = build_on_ice_at_event(
            parsed_shifts=parsed_shifts,
            event_abs_seconds=row["event_abs_seconds"],
            home_team_id=home_team_id,
            away_team_id=away_team_id,
        )
        row["home_on_ice_ids"] = list(on_ice.home_on_ice_ids)
        row["away_on_ice_ids"] = list(on_ice.away_on_ice_ids)
        row["source_quality"] = on_ice.source_quality

        # Goalie / skater counts from situation_code (authoritative)
        away_sk, home_sk, away_g, home_g = _decode_situation_code(row["situation_code"])
        row["home_skaters_on_ice"] = home_sk
        row["away_skaters_on_ice"] = away_sk
        row["home_goalie_on_ice"] = home_g
        row["away_goalie_on_ice"] = away_g
        if row["period_type"] == "SO":
            row["strength_state"] = None
        elif row["source_quality"] != "FULL":
            row["strength_state"] = None
        elif home_sk and away_sk and home_g is not None and away_g is not None:
            row["strength_state"] = derive_strength_state(
                home_skaters=home_sk, away_skaters=away_sk,
                home_goalie=home_g, away_goalie=away_g,
            )

        rows.append(row)

    return pd.DataFrame(rows)
