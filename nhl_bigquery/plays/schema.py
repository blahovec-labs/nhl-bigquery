"""PLAYS_SCHEMA: single source of truth for the nhl_plays table.

This file is built up in groups (identifiers, time, event classification,
coords, players, shot details, penalty details, on-ice state, score state,
team context, source-quality). Authored across multiple tasks to keep
each commit reviewable.
"""

from __future__ import annotations

from nhl_bigquery.schema import ColumnSpec, PartitioningSpec


def get_partitioning() -> PartitioningSpec:
    return PartitioningSpec(
        field="game_date",
        type="DAY",
        clustering=["home_team_abbrev", "away_team_abbrev", "game_id"],
    )


PLAYS_SCHEMA: list[ColumnSpec] = [
    # -------------------------------------------------------------------------
    # Group A: Identifiers + time/period
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="game_id",
        type="INT64",
        mode="REQUIRED",
        short_description="NHL unique game identifier.",
        business_definition=(
            "Stable integer identifying a single NHL game across all data sources. "
            "Use as the canonical join key to games, boxscore_stats, shifts, and "
            "game_officials. Format: <season-year><game-type:02-04><sequence>."
        ),
        semantic_tags=["identifier", "join_key", "nhl_canonical"],
        valid_range=None, valid_values=None, example_value=2024020001,
        gotchas=[
            "game_type digit: 01=preseason, 02=regular, 03=playoffs, 04=all-star.",
        ],
        nhl_api_equivalent="id",
        nhl_api_source_field="id",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="event_id",
        type="INT64",
        mode="REQUIRED",
        short_description="NHL event ID within a game.",
        business_definition=(
            "Per-game sequential event identifier from the play-by-play API. Unique "
            "within (game_id, event_id). Use sort_order for stable ordering of plays "
            "in display contexts."
        ),
        semantic_tags=["identifier", "join_key"],
        valid_range=None, valid_values=None, example_value=12,
        gotchas=[
            "event_id is unique per game, NOT globally — always join with game_id.",
        ],
        nhl_api_equivalent="eventId",
        nhl_api_source_field="eventId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="sort_order",
        type="INT64",
        mode="NULLABLE",
        short_description="Stable display ordering of events within a game.",
        business_definition=(
            "Sequential integer (1..N) assigned during ingestion that reflects the "
            "intended display ordering of plays within a game. Use this instead of "
            "event_id for ordering — event_id can have gaps."
        ),
        semantic_tags=["ordering"],
        valid_range=(1.0, 2000.0), valid_values=None, example_value=42,
        gotchas=[],
        nhl_api_equivalent="sortOrder",
        nhl_api_source_field="sortOrder",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="season",
        type="INT64",
        mode="REQUIRED",
        short_description="Season start year (e.g., 2024 for 2024-25).",
        business_definition=(
            "Four-digit year denoting the season starting year. The 2024-25 NHL "
            "season is season=2024. Useful for season-grain filters and joins."
        ),
        semantic_tags=["temporal", "identifier"],
        valid_range=(2010.0, 2050.0), valid_values=None, example_value=2024,
        gotchas=[
            "Always the START year — playoff games in May 2025 still have season=2024.",
        ],
        nhl_api_equivalent="season (first 4 digits, e.g. 20242025 → 2024)",
        nhl_api_source_field="season",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="game_date",
        type="DATE",
        mode="REQUIRED",
        short_description="Calendar date the game was played (local venue).",
        business_definition=(
            "Date the game was played, sourced from gameDate. Serves as the BigQuery "
            "partition key for this table."
        ),
        semantic_tags=["temporal", "identifier"],
        valid_range=None, valid_values=None, example_value="2024-10-08",
        gotchas=[],
        nhl_api_equivalent="gameDate",
        nhl_api_source_field="gameDate",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="game_type",
        type="STRING",
        mode="NULLABLE",
        short_description="Game type code (PR/R/P/AS).",
        business_definition=(
            "Game type derived from the game_id type digit. PR=preseason, R=regular, "
            "P=playoffs, AS=all-star. Most analyses should filter game_type='R' for "
            "regular-season rate stats."
        ),
        semantic_tags=["identifier"],
        valid_range=None, valid_values=["PR", "R", "P", "AS"], example_value="R",
        gotchas=[],
        nhl_api_equivalent="gameType (numeric → coded)",
        nhl_api_source_field="gameType",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="period",
        type="INT64",
        mode="NULLABLE",
        short_description="Period number (1-3 regulation, 4+ OT, 5 SO).",
        business_definition=(
            "Period number when the event occurred. 1-3 are regulation, 4 is "
            "regular-season OT (3v3, 5 min) or playoff OT (5v5, continuous "
            "20-min periods), and 5 is the shootout (regular season only)."
        ),
        semantic_tags=["temporal", "pitch_context"],
        valid_range=(1.0, 10.0), valid_values=None, example_value=2,
        gotchas=[
            "Playoff games can have period > 4 for multi-OT thrillers.",
        ],
        nhl_api_equivalent="periodDescriptor.number",
        nhl_api_source_field="periodDescriptor.number",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="period_type",
        type="STRING",
        mode="NULLABLE",
        short_description="Period type: REG, OT, SO.",
        business_definition=(
            "Type of period the event occurred in. REG=regulation, OT=overtime, "
            "SO=shootout. Use this to filter shootout events out of skater stats."
        ),
        semantic_tags=["temporal", "pitch_context"],
        valid_range=None, valid_values=["REG", "OT", "SO"], example_value="REG",
        gotchas=[
            "Shootout (SO) events have NULL time_in_period and event_abs_seconds.",
        ],
        nhl_api_equivalent="periodDescriptor.periodType",
        nhl_api_source_field="periodDescriptor.periodType",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="time_in_period",
        type="STRING",
        mode="NULLABLE",
        short_description="MM:SS elapsed in the current period.",
        business_definition=(
            "Elapsed time within the current period as MM:SS. 0:00 means the start "
            "of the period. NULL for shootout events."
        ),
        semantic_tags=["temporal"],
        valid_range=None, valid_values=None, example_value="14:32",
        gotchas=[
            "String, not duration — use event_abs_seconds for arithmetic.",
        ],
        nhl_api_equivalent="timeInPeriod",
        nhl_api_source_field="timeInPeriod",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="time_remaining",
        type="STRING",
        mode="NULLABLE",
        short_description="MM:SS remaining in the current period.",
        business_definition=(
            "Time remaining in the current period as MM:SS. The complement of "
            "time_in_period (sums to 20:00 in regulation, 5:00 in regular-season OT)."
        ),
        semantic_tags=["temporal"],
        valid_range=None, valid_values=None, example_value="5:28",
        gotchas=[],
        nhl_api_equivalent="timeRemaining",
        nhl_api_source_field="timeRemaining",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="event_abs_seconds",
        type="INT64",
        mode="NULLABLE",
        short_description="Derived: absolute seconds from game start.",
        business_definition=(
            "Derived during ingestion: (period - 1) * 1200 + parse_mmss(time_in_period). "
            "NULL for shootout events. Use this for time-based joins (shifts) and "
            "windowed aggregations within a game."
        ),
        semantic_tags=["temporal", "derived"],
        valid_range=(0.0, 12000.0), valid_values=None, example_value=872,
        gotchas=[
            "Derived field, not from the NHL API. NULL for shootout events.",
        ],
        nhl_api_equivalent=None,
        nhl_api_source_field="(derived from periodDescriptor.number + timeInPeriod)",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Group B: Event classification + coordinates
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="event_type",
        type="STRING",
        mode="NULLABLE",
        short_description="High-level event type.",
        business_definition=(
            "Event classification — one of GOAL, SHOT, MISSED_SHOT, BLOCKED_SHOT, "
            "HIT, FACEOFF, GIVEAWAY, TAKEAWAY, PENALTY, STOPPAGE, PERIOD_START, "
            "PERIOD_END, GAME_END, SHOOTOUT_COMPLETE, DELAYED_PENALTY. Drives "
            "which player-role columns are populated."
        ),
        semantic_tags=["event_context", "classification"],
        valid_range=None,
        valid_values=[
            "GOAL", "SHOT", "MISSED_SHOT", "BLOCKED_SHOT", "HIT", "FACEOFF",
            "GIVEAWAY", "TAKEAWAY", "PENALTY", "STOPPAGE", "PERIOD_START",
            "PERIOD_END", "GAME_END", "SHOOTOUT_COMPLETE", "DELAYED_PENALTY",
        ],
        example_value="SHOT",
        gotchas=[
            "BLOCKED_SHOT: shooter_id is the attempt player; blocker_id is the defender.",
            "STOPPAGE includes whistles, icings, offsides; check event_type_desc for detail.",
        ],
        nhl_api_equivalent="typeDescKey (uppercased)",
        nhl_api_source_field="typeDescKey",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="event_type_desc",
        type="STRING",
        mode="NULLABLE",
        short_description="Detailed event sub-description (raw API).",
        business_definition=(
            "Lower-case key from the NHL API (e.g., 'goal', 'shot-on-goal', "
            "'missed-shot', 'blocked-shot', 'hit', 'faceoff', 'giveaway', "
            "'takeaway', 'penalty', 'stoppage'). Preserved verbatim for "
            "advanced filtering."
        ),
        semantic_tags=["event_context"],
        valid_range=None, valid_values=None, example_value="shot-on-goal",
        gotchas=[],
        nhl_api_equivalent="typeDescKey",
        nhl_api_source_field="typeDescKey",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="situation_code",
        type="STRING",
        mode="NULLABLE",
        short_description=(
            "4-digit on-ice strength code "
            "(away_goalie/away_skaters/home_skaters/home_goalie)."
        ),
        business_definition=(
            "4-character code from the NHL API encoding (away_goalie, away_skaters, "
            "home_skaters, home_goalie) at the time of the event. '1551' is "
            "even-strength 5v5 with both goalies in. '1451' is away PP (4 away "
            "skaters vs. 5 home skaters, both goalies in)."
        ),
        semantic_tags=["event_context", "on_ice"],
        valid_range=None, valid_values=None, example_value="1551",
        gotchas=[
            "Order is away_goalie, away_skaters, home_skaters, home_goalie.",
            "Position 0/3 (goalie flags): 1 means goalie on ice, 0 means pulled.",
        ],
        nhl_api_equivalent="situationCode",
        nhl_api_source_field="situationCode",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="x_coord",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="X coordinate on the ice surface (feet from center red line).",
        business_definition=(
            "X coordinate of the event location in feet. The ice surface is 200 ft "
            "long, with x=0 at the center red line, x=+89 at one goal line and "
            "x=-89 at the other. NULL for events without a location (PERIOD_START, "
            "GAME_END, STOPPAGE in some cases)."
        ),
        semantic_tags=["location"],
        valid_range=(-100.0, 100.0), valid_values=None, example_value=-42.0,
        gotchas=[
            "Coordinate orientation switches between periods 1 and 2 (teams change ends).",
            "Pre-2010 games may have NULL x_coord even for shot events.",
        ],
        nhl_api_equivalent="details.xCoord",
        nhl_api_source_field="details.xCoord",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="y_coord",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Y coordinate on the ice surface (feet from center line).",
        business_definition=(
            "Y coordinate of the event location in feet. The ice surface is 85 ft "
            "wide, so y ranges from -42.5 to +42.5. NULL for events without a "
            "location."
        ),
        semantic_tags=["location"],
        valid_range=(-42.5, 42.5), valid_values=None, example_value=-7.5,
        gotchas=[
            "Pre-2010 games may have NULL y_coord even for shot events.",
        ],
        nhl_api_equivalent="details.yCoord",
        nhl_api_source_field="details.yCoord",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="zone_code",
        type="STRING",
        mode="NULLABLE",
        short_description="Single-letter zone code: O, D, N (offensive, defensive, neutral).",
        business_definition=(
            "Zone of the ice surface where the event occurred, relative to the "
            "event_owner_team. O=offensive (attacking) zone, D=defensive zone, "
            "N=neutral zone."
        ),
        semantic_tags=["location"],
        valid_range=None, valid_values=["O", "D", "N"], example_value="O",
        gotchas=[
            "Zone is relative to event_owner_team — a SHOT by Team A has zone=O "
            "(their offensive zone), while a HIT by Team A in Team B's offensive "
            "zone has zone=D from A's perspective.",
        ],
        nhl_api_equivalent="details.zoneCode",
        nhl_api_source_field="details.zoneCode",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="zone_descriptor",
        type="STRING",
        mode="NULLABLE",
        short_description="Human-readable zone name.",
        business_definition=(
            "Full English name for the zone (e.g., 'offensive', 'defensive', 'neutral'). "
            "Display-only; use zone_code for filtering."
        ),
        semantic_tags=["location"],
        valid_range=None, valid_values=None, example_value="offensive",
        gotchas=[],
        nhl_api_equivalent=None,
        nhl_api_source_field="(derived from details.zoneCode)",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Group C: Players (wide-flat sparse)
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="event_owner_team_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Team ID that 'owns' this event (the actor).",
        business_definition=(
            "NHL team_id of the team performing the event. For a SHOT, this is "
            "the shooting team; for a HIT, the hitting team; for a FACEOFF, the "
            "team that won the faceoff (NULL if details.winningPlayerId is NULL)."
        ),
        semantic_tags=["identifier", "join_key", "team"],
        valid_range=None, valid_values=None, example_value=10,
        gotchas=[],
        nhl_api_equivalent="details.eventOwnerTeamId",
        nhl_api_source_field="details.eventOwnerTeamId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="shooter_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Player attempting the shot (SHOT/MISSED_SHOT/GOAL/BLOCKED_SHOT).",
        business_definition=(
            "NHL Player ID of the player attempting the shot. Populated for "
            "event_type IN ('SHOT', 'MISSED_SHOT', 'GOAL', 'BLOCKED_SHOT'). For "
            "BLOCKED_SHOT, shooter_id is the *attempt* player; use blocker_id for "
            "the defender."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8478402,
        gotchas=[
            "BLOCKED_SHOT events: shooter_id = attempt; blocker_id = defender.",
            "NULL for non-shot events.",
        ],
        nhl_api_equivalent="details.shootingPlayerId | details.scoringPlayerId",
        nhl_api_source_field="details.shootingPlayerId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="goalie_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Goalie facing the shot (SHOT/MISSED_SHOT/GOAL).",
        business_definition=(
            "NHL Player ID of the goaltender in net facing the shot. NULL for "
            "empty-net situations and for events without a goalie context."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8475883,
        gotchas=[
            "NULL on empty-net goals — check home_goalie_on_ice / away_goalie_on_ice.",
        ],
        nhl_api_equivalent="details.goalieInNetId",
        nhl_api_source_field="details.goalieInNetId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="scorer_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Goal scorer (GOAL only).",
        business_definition=(
            "NHL Player ID of the goal scorer. Populated only for event_type='GOAL'. "
            "Same player as shooter_id, but split out for clarity in goal-specific "
            "queries."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8478402,
        gotchas=[
            "Always equals shooter_id when event_type='GOAL'.",
        ],
        nhl_api_equivalent="details.scoringPlayerId",
        nhl_api_source_field="details.scoringPlayerId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="primary_assist_id",
        type="INT64",
        mode="NULLABLE",
        short_description="First assister (GOAL).",
        business_definition=(
            "NHL Player ID of the primary assister. NULL if no assists were awarded "
            "(unassisted goal)."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8479318,
        gotchas=[],
        nhl_api_equivalent="details.assist1PlayerId",
        nhl_api_source_field="details.assist1PlayerId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="secondary_assist_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Second assister (GOAL).",
        business_definition=(
            "NHL Player ID of the secondary assister. NULL if only one assist was "
            "awarded or if unassisted."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8477956,
        gotchas=[],
        nhl_api_equivalent="details.assist2PlayerId",
        nhl_api_source_field="details.assist2PlayerId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="hitter_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Player delivering the hit (HIT).",
        business_definition=(
            "NHL Player ID of the player delivering the body check. Populated only "
            "for event_type='HIT'."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8476881,
        gotchas=[],
        nhl_api_equivalent="details.hittingPlayerId",
        nhl_api_source_field="details.hittingPlayerId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="hittee_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Player receiving the hit (HIT).",
        business_definition=(
            "NHL Player ID of the player on the receiving end of the body check. "
            "Populated only for event_type='HIT'."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8478402,
        gotchas=[],
        nhl_api_equivalent="details.hitteePlayerId",
        nhl_api_source_field="details.hitteePlayerId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="winning_player_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Faceoff winner (FACEOFF).",
        business_definition=(
            "NHL Player ID of the player who won the faceoff. Populated only for "
            "event_type='FACEOFF'."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8478403,
        gotchas=[],
        nhl_api_equivalent="details.winningPlayerId",
        nhl_api_source_field="details.winningPlayerId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="losing_player_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Faceoff loser (FACEOFF).",
        business_definition=(
            "NHL Player ID of the player who lost the faceoff. Populated only for "
            "event_type='FACEOFF'."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8474157,
        gotchas=[],
        nhl_api_equivalent="details.losingPlayerId",
        nhl_api_source_field="details.losingPlayerId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="drawn_by_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Player who drew a penalty (PENALTY).",
        business_definition=(
            "NHL Player ID of the player who drew (was fouled by) the penalty. "
            "Populated only for event_type='PENALTY'."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8478402,
        gotchas=[
            "NULL for unsportsmanlike / bench / coach's challenge penalties.",
        ],
        nhl_api_equivalent="details.drawnByPlayerId",
        nhl_api_source_field="details.drawnByPlayerId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="served_by_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Player serving a penalty for a teammate (PENALTY).",
        business_definition=(
            "NHL Player ID of the player serving the penalty. Differs from "
            "penalty_player_id when a teammate serves (e.g., goalie/bench minors)."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8474157,
        gotchas=[],
        nhl_api_equivalent="details.servedByPlayerId",
        nhl_api_source_field="details.servedByPlayerId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="penalty_player_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Penalty offender (PENALTY).",
        business_definition=(
            "NHL Player ID of the player who committed the penalty. May differ "
            "from served_by_id when a teammate serves."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8476881,
        gotchas=[],
        nhl_api_equivalent="details.committedByPlayerId",
        nhl_api_source_field="details.committedByPlayerId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="blocker_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Shot blocker (BLOCKED_SHOT).",
        business_definition=(
            "NHL Player ID of the player who blocked the shot. Populated only for "
            "event_type='BLOCKED_SHOT'. shooter_id holds the attempt player."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8470794,
        gotchas=[],
        nhl_api_equivalent="details.blockingPlayerId",
        nhl_api_source_field="details.blockingPlayerId",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="committed_by_id",
        type="INT64",
        mode="NULLABLE",
        short_description="Player who committed a turnover (GIVEAWAY/TAKEAWAY).",
        business_definition=(
            "NHL Player ID of the player who committed a giveaway or executed a "
            "takeaway. Populated for event_type IN ('GIVEAWAY', 'TAKEAWAY')."
        ),
        semantic_tags=["identifier", "join_key", "player_event"],
        valid_range=None, valid_values=None, example_value=8478402,
        gotchas=[
            "For GIVEAWAY, this is the player who turned over the puck.",
            "For TAKEAWAY, this is the player who took it from the opponent.",
        ],
        nhl_api_equivalent="details.playerId",
        nhl_api_source_field="details.playerId",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Group D: Shot details + penalty details + score state + team context
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="shot_type",
        type="STRING",
        mode="NULLABLE",
        short_description="Shot type (wrist, slap, snap, backhand, tip-in, ...).",
        business_definition=(
            "Type of shot taken on SHOT, MISSED_SHOT, GOAL, BLOCKED_SHOT events. "
            "Common values: wrist, slap, snap, backhand, tip-in, deflected, "
            "wrap-around, poke."
        ),
        semantic_tags=["event_context"],
        valid_range=None,
        valid_values=["wrist", "slap", "snap", "backhand", "tip-in", "deflected",
                      "wrap-around", "poke", "bat"],
        example_value="wrist",
        gotchas=[
            "Lowercase from API — preserved verbatim.",
        ],
        nhl_api_equivalent="details.shotType",
        nhl_api_source_field="details.shotType",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="penalty_minutes",
        type="INT64",
        mode="NULLABLE",
        short_description="Penalty duration in minutes (PENALTY).",
        business_definition=(
            "Number of minutes assessed for the penalty. Common values: 2 (minor), "
            "4 (double minor), 5 (major), 10 (misconduct). Populated only for "
            "event_type='PENALTY'."
        ),
        semantic_tags=["event_context"],
        valid_range=(2.0, 20.0), valid_values=None, example_value=2,
        gotchas=[],
        nhl_api_equivalent="details.duration",
        nhl_api_source_field="details.duration",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="penalty_severity",
        type="STRING",
        mode="NULLABLE",
        short_description="Penalty severity code (MIN/MAJ/MIS/BEN/MAT/GAM/PS).",
        business_definition=(
            "Severity classification. MIN=minor, MAJ=major, MIS=misconduct, "
            "BEN=bench minor, MAT=match, GAM=game misconduct, PS=penalty shot."
        ),
        semantic_tags=["event_context"],
        valid_range=None,
        valid_values=["MIN", "MAJ", "MIS", "BEN", "MAT", "GAM", "PS"],
        example_value="MIN",
        gotchas=[],
        nhl_api_equivalent="details.typeCode (mapped)",
        nhl_api_source_field="details.typeCode",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="penalty_type_code",
        type="STRING",
        mode="NULLABLE",
        short_description="Raw NHL penalty type code.",
        business_definition=(
            "Short code from the NHL API identifying the specific infraction "
            "(e.g., 'HOOK' for hooking, 'TRIP' for tripping). Preserved verbatim."
        ),
        semantic_tags=["event_context"],
        valid_range=None, valid_values=None, example_value="HOOK",
        gotchas=[],
        nhl_api_equivalent="details.typeCode",
        nhl_api_source_field="details.typeCode",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="penalty_type_desc",
        type="STRING",
        mode="NULLABLE",
        short_description="Human-readable penalty description.",
        business_definition=(
            "Full English description of the penalty (e.g., 'Hooking', 'Tripping'). "
            "Display-only; use penalty_type_code for filtering."
        ),
        semantic_tags=["event_context"],
        valid_range=None, valid_values=None, example_value="Hooking",
        gotchas=[],
        nhl_api_equivalent="details.descKey",
        nhl_api_source_field="details.descKey",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="home_score_before",
        type="INT64",
        mode="NULLABLE",
        short_description="Home team score before this event.",
        business_definition=(
            "Home team goal count immediately before the event resolves. For a "
            "GOAL event scored by home, home_score_after = home_score_before + 1."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 20.0), valid_values=None, example_value=2,
        gotchas=[],
        nhl_api_equivalent=None,
        nhl_api_source_field="(derived: details.homeScore minus 1 if this is a home GOAL)",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="away_score_before",
        type="INT64",
        mode="NULLABLE",
        short_description="Away team score before this event.",
        business_definition=(
            "Away team goal count immediately before the event resolves."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 20.0), valid_values=None, example_value=1,
        gotchas=[],
        nhl_api_equivalent=None,
        nhl_api_source_field="(derived: details.awayScore minus 1 if this is an away GOAL)",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="home_score_after",
        type="INT64",
        mode="NULLABLE",
        short_description="Home team score after this event.",
        business_definition=(
            "Home team goal count immediately after the event resolves."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 20.0), valid_values=None, example_value=3,
        gotchas=[],
        nhl_api_equivalent="details.homeScore",
        nhl_api_source_field="details.homeScore",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="away_score_after",
        type="INT64",
        mode="NULLABLE",
        short_description="Away team score after this event.",
        business_definition=(
            "Away team goal count immediately after the event resolves."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 20.0), valid_values=None, example_value=1,
        gotchas=[],
        nhl_api_equivalent="details.awayScore",
        nhl_api_source_field="details.awayScore",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="home_team_id",
        type="INT64",
        mode="REQUIRED",
        short_description="NHL team ID of the home team.",
        business_definition=(
            "NHL team ID for the home team in this game. Stable across seasons; "
            "use to join to team dimension tables."
        ),
        semantic_tags=["identifier", "join_key", "team"],
        valid_range=None, valid_values=None, example_value=10,
        gotchas=[],
        nhl_api_equivalent="homeTeam.id",
        nhl_api_source_field="homeTeam.id",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="away_team_id",
        type="INT64",
        mode="REQUIRED",
        short_description="NHL team ID of the away team.",
        business_definition=(
            "NHL team ID for the away team in this game. Stable across seasons."
        ),
        semantic_tags=["identifier", "join_key", "team"],
        valid_range=None, valid_values=None, example_value=6,
        gotchas=[],
        nhl_api_equivalent="awayTeam.id",
        nhl_api_source_field="awayTeam.id",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="home_team_abbrev",
        type="STRING",
        mode="NULLABLE",
        short_description="Home team 3-letter abbreviation.",
        business_definition=(
            "Three-letter abbreviation for the home team (e.g., TOR, EDM, NYR). "
            "Denormalized from games for partition-prune-friendly filters."
        ),
        semantic_tags=["team", "identifier"],
        valid_range=None, valid_values=None, example_value="TOR",
        gotchas=[
            "Abbreviations changed for relocations (e.g., ARI → UTA in 2024).",
        ],
        nhl_api_equivalent="homeTeam.abbrev",
        nhl_api_source_field="homeTeam.abbrev",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="away_team_abbrev",
        type="STRING",
        mode="NULLABLE",
        short_description="Away team 3-letter abbreviation.",
        business_definition=(
            "Three-letter abbreviation for the away team."
        ),
        semantic_tags=["team", "identifier"],
        valid_range=None, valid_values=None, example_value="MTL",
        gotchas=[],
        nhl_api_equivalent="awayTeam.abbrev",
        nhl_api_source_field="awayTeam.abbrev",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Group E: On-ice state + source quality
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="home_on_ice_ids",
        type="INT64",
        mode="REPEATED",
        short_description="Home team player IDs on the ice during this event.",
        business_definition=(
            "Array of NHL Player IDs for every home-team player on the ice at the "
            "moment of this event. Derived during ingestion by joining the event's "
            "absolute time to each player's shift intervals (half-open). Empty "
            "array for shootout events and for pre-shift-era games."
        ),
        semantic_tags=["on_ice", "derived"],
        valid_range=None, valid_values=None, example_value=[8478402, 8479318],
        gotchas=[
            "Empty for shootout events (period_type='SO').",
            "Empty for games where source_quality='NO_SHIFTS'.",
            "May have fewer than 5 members during goalie-pulled situations.",
        ],
        nhl_api_equivalent=None,
        nhl_api_source_field="(derived from shift-charts + event time)",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="away_on_ice_ids",
        type="INT64",
        mode="REPEATED",
        short_description="Away team player IDs on the ice during this event.",
        business_definition=(
            "Array of NHL Player IDs for every away-team player on the ice at "
            "the moment of this event. Same derivation rules as home_on_ice_ids."
        ),
        semantic_tags=["on_ice", "derived"],
        valid_range=None, valid_values=None, example_value=[8474157, 8476881],
        gotchas=[
            "Empty for shootout events and for source_quality='NO_SHIFTS' rows.",
        ],
        nhl_api_equivalent=None,
        nhl_api_source_field="(derived from shift-charts + event time)",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="home_skaters_on_ice",
        type="INT64",
        mode="NULLABLE",
        short_description="Count of home skaters on ice (excludes goalie).",
        business_definition=(
            "Number of home-team skaters on the ice at event time, excluding the "
            "goaltender. Typically 5; can be 6 with goalie pulled, 4 on a PK, "
            "3 in 3v3 OT."
        ),
        semantic_tags=["on_ice", "derived"],
        valid_range=(0.0, 6.0), valid_values=None, example_value=5,
        gotchas=[],
        nhl_api_equivalent=None,
        nhl_api_source_field="(derived from home_on_ice_ids)",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="away_skaters_on_ice",
        type="INT64",
        mode="NULLABLE",
        short_description="Count of away skaters on ice (excludes goalie).",
        business_definition=(
            "Number of away-team skaters on the ice at event time, excluding the "
            "goaltender."
        ),
        semantic_tags=["on_ice", "derived"],
        valid_range=(0.0, 6.0), valid_values=None, example_value=5,
        gotchas=[],
        nhl_api_equivalent=None,
        nhl_api_source_field="(derived from away_on_ice_ids)",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="home_goalie_on_ice",
        type="BOOL",
        mode="NULLABLE",
        short_description="Is the home goalie on the ice for this event?",
        business_definition=(
            "True if the home goaltender is on the ice at event time. False when "
            "the home goalie has been pulled for an extra attacker."
        ),
        semantic_tags=["on_ice", "derived"],
        valid_range=None, valid_values=None, example_value=True,
        gotchas=[],
        nhl_api_equivalent=None,
        nhl_api_source_field="(derived from situationCode + on-ice IDs)",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="away_goalie_on_ice",
        type="BOOL",
        mode="NULLABLE",
        short_description="Is the away goalie on the ice for this event?",
        business_definition=(
            "True if the away goaltender is on the ice at event time."
        ),
        semantic_tags=["on_ice", "derived"],
        valid_range=None, valid_values=None, example_value=True,
        gotchas=[],
        nhl_api_equivalent=None,
        nhl_api_source_field="(derived from situationCode + on-ice IDs)",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="strength_state",
        type="STRING",
        mode="NULLABLE",
        short_description="Strength code: EV, PP_H, PP_A, SH_H, SH_A, EN_H, EN_A, 4v4, 3v3.",
        business_definition=(
            "Derived strength state at event time. EV=even strength 5v5; "
            "PP_H/PP_A=power play for home/away; SH_H/SH_A=shorthanded; "
            "EN_H/EN_A=empty net for home/away (goalie pulled); "
            "4v4=coincidental majors; 3v3=regular-season OT."
        ),
        semantic_tags=["on_ice", "derived"],
        valid_range=None,
        valid_values=["EV", "PP_H", "PP_A", "SH_H", "SH_A", "EN_H", "EN_A", "4v4", "3v3"],
        example_value="EV",
        gotchas=[
            "NULL for shootout events and for source_quality='NO_SHIFTS' rows.",
        ],
        nhl_api_equivalent=None,
        nhl_api_source_field="(derived from skater counts + goalie flags)",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="source_quality",
        type="STRING",
        mode="NULLABLE",
        short_description="Ingestion source-quality flag (FULL, NO_SHIFTS, PARTIAL).",
        business_definition=(
            "Indicates the completeness of source data for this row. FULL = both "
            "play-by-play and shift-charts were available and merged. NO_SHIFTS = "
            "shift-charts unavailable (likely pre-shift-era game); on-ice arrays "
            "are empty. PARTIAL = play-by-play available but partial shift coverage."
        ),
        semantic_tags=["meta", "derived"],
        valid_range=None,
        valid_values=["FULL", "NO_SHIFTS", "PARTIAL"],
        example_value="FULL",
        gotchas=[
            "Filter source_quality='FULL' for analyses that depend on on-ice arrays.",
        ],
        nhl_api_equivalent=None,
        nhl_api_source_field="(set by ingestion)",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="ingested_at",
        type="TIMESTAMP",
        mode="REQUIRED",
        short_description="Timestamp the row was ingested.",
        business_definition=(
            "UTC timestamp when this row was written by nhl-bigquery sync. Useful "
            "for tracking freshness and pinpointing the run that wrote a given row."
        ),
        semantic_tags=["meta"],
        valid_range=None, valid_values=None, example_value="2026-05-22T17:00:00Z",
        gotchas=[],
        nhl_api_equivalent=None,
        nhl_api_source_field="(set by ingestion)",
        deprecated_in_year=None,
    ),
]
