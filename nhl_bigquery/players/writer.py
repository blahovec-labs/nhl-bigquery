"""dim_players upsert writer: stage table + MERGE.

Unlike the chunked plays/games writers (DELETE-then-INSERT keyed on
partition), dim_players is unpartitioned and per-row mutable. We:
  1. load_table_from_dataframe(df) into a temporary `_stage_<uuid>` table
  2. MERGE the stage into the target on player_id
  3. DROP TABLE the stage
This is fully idempotent — re-running with the same df is a no-op.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import pandas as pd
from google.cloud import bigquery

log = logging.getLogger(__name__)


_MERGE_TEMPLATE = """
MERGE `{target}` t
USING `{source}` s
ON t.player_id = s.player_id
WHEN MATCHED THEN UPDATE SET
  first_name = s.first_name,
  last_name = s.last_name,
  full_name = s.full_name,
  position_code = s.position_code,
  sweater_number = s.sweater_number,
  current_team_abbrev = s.current_team_abbrev,
  shoots_catches = s.shoots_catches,
  birth_date = s.birth_date,
  birth_country = s.birth_country,
  height_inches = s.height_inches,
  weight_pounds = s.weight_pounds,
  headshot_url = s.headshot_url,
  ingested_at = s.ingested_at
WHEN NOT MATCHED THEN INSERT (
  player_id, first_name, last_name, full_name, position_code,
  sweater_number, current_team_abbrev, shoots_catches, birth_date,
  birth_country, height_inches, weight_pounds, headshot_url, ingested_at
) VALUES (
  s.player_id, s.first_name, s.last_name, s.full_name, s.position_code,
  s.sweater_number, s.current_team_abbrev, s.shoots_catches, s.birth_date,
  s.birth_country, s.height_inches, s.weight_pounds, s.headshot_url, s.ingested_at
)
"""


def build_merge_sql(*, target: str, source: str) -> str:
    return _MERGE_TEMPLATE.format(target=target, source=source).strip()


_DISCOVERY_TEMPLATE = """
WITH role_ids AS (
  SELECT shooter_id AS player_id FROM `{plays}`
  UNION ALL SELECT goalie_id FROM `{plays}`
  UNION ALL SELECT scorer_id FROM `{plays}`
  UNION ALL SELECT primary_assist_id FROM `{plays}`
  UNION ALL SELECT secondary_assist_id FROM `{plays}`
  UNION ALL SELECT hitter_id FROM `{plays}`
  UNION ALL SELECT hittee_id FROM `{plays}`
  UNION ALL SELECT winning_player_id FROM `{plays}`
  UNION ALL SELECT losing_player_id FROM `{plays}`
  UNION ALL SELECT drawn_by_id FROM `{plays}`
  UNION ALL SELECT served_by_id FROM `{plays}`
  UNION ALL SELECT penalty_player_id FROM `{plays}`
  UNION ALL SELECT blocker_id FROM `{plays}`
  UNION ALL SELECT committed_by_id FROM `{plays}`
  UNION ALL SELECT player_id FROM `{plays}`, UNNEST(home_on_ice_ids) AS player_id
  UNION ALL SELECT player_id FROM `{plays}`, UNNEST(away_on_ice_ids) AS player_id
),
distinct_ids AS (
  SELECT DISTINCT player_id FROM role_ids WHERE player_id IS NOT NULL
)
SELECT d.player_id
FROM distinct_ids d
LEFT JOIN `{players}` p USING (player_id)
WHERE p.player_id IS NULL
"""


def select_missing_player_ids_sql(*, plays_table: str, players_table: str) -> str:
    return _DISCOVERY_TEMPLATE.format(plays=plays_table, players=players_table).strip()


_NULLABLE_INT_COLUMNS = ("sweater_number", "height_inches", "weight_pounds")


def _coerce_nullable_ints(df: pd.DataFrame) -> pd.DataFrame:
    """Pandas promotes int columns to float64 when any cell is NaN, which BQ
    rejects on load against an INT64 column. Cast those columns to pandas's
    nullable Int64 dtype so BQ sees integers + nulls correctly.
    """
    df = df.copy()
    for col in _NULLABLE_INT_COLUMNS:
        if col in df.columns and str(df[col].dtype) == "float64":
            df[col] = df[col].astype("Int64")
    return df


def upsert_players(
    client: bigquery.Client,
    *,
    target: str,
    df: pd.DataFrame,
) -> int:
    """MERGE the DataFrame into target. Returns rows merged."""
    if df.empty:
        log.info("upsert_players: empty df, skipping")
        return 0

    df = _coerce_nullable_ints(df)

    target_parts = target.split(".")
    if len(target_parts) != 3:
        raise ValueError(f"expected project.dataset.table, got {target!r}")
    proj, ds, _table = target_parts
    stage = f"{proj}.{ds}._dim_players_stage_{uuid.uuid4().hex[:8]}"

    load_job = client.load_table_from_dataframe(
        df, stage,
        job_config=bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        ),
    )
    load_job.result()
    log.info("staged %d rows in %s", len(df), stage)

    merge_sql = build_merge_sql(target=target, source=stage)
    client.query(merge_sql).result()
    log.info("merged into %s", target)

    client.query(f"DROP TABLE `{stage}`").result()
    log.info("dropped stage %s", stage)
    return len(df)
