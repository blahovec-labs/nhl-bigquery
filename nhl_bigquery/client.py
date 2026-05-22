"""NHLAPIClient: thin wrapper around api-web.nhle.com/v1 with retry + politeness.

Shift-chart data lives on the legacy stats API (api.nhle.com/stats/rest/en),
not the v1 game-center API. LEGACY_STATS_URL is used for that endpoint only.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Final

import requests

log = logging.getLogger(__name__)

BASE_URL: Final[str] = "https://api-web.nhle.com/v1"
LEGACY_STATS_URL: Final[str] = "https://api.nhle.com/stats/rest/en"
DEFAULT_SLEEP_SECONDS: Final[float] = 1.0
DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
DEFAULT_MAX_RETRIES: Final[int] = 5


class NHLAPIClient:
    """Polite, retry-aware client for the public NHL API."""

    def __init__(
        self,
        sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_url: str = BASE_URL,
    ) -> None:
        self.sleep_seconds = sleep_seconds
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.base_url = base_url

    def _get_url(self, url: str) -> dict[str, Any]:
        """Fetch *url* with retry + exponential backoff."""
        attempt = 0
        last_err: Exception | None = None
        while attempt < self.max_retries:
            attempt += 1
            try:
                resp = requests.get(url, timeout=self.timeout_seconds)
                if 500 <= resp.status_code < 600 or resp.status_code == 429:
                    raise requests.HTTPError(f"{resp.status_code} {resp.reason}")
                resp.raise_for_status()
                if self.sleep_seconds:
                    time.sleep(self.sleep_seconds)
                return resp.json()
            except Exception as e:
                last_err = e
                backoff = self.sleep_seconds * (2 ** (attempt - 1)) if self.sleep_seconds else 0
                log.warning("GET %s attempt %d failed: %s; backoff %.1fs",
                            url, attempt, e, backoff)
                if backoff:
                    time.sleep(backoff)
        assert last_err is not None
        raise last_err

    def _get(self, path: str) -> dict[str, Any]:
        return self._get_url(f"{self.base_url}{path}")

    def get_score(self, date: str) -> dict[str, Any]:
        return self._get(f"/score/{date}")

    def get_standings(self, date: str) -> dict[str, Any]:
        return self._get(f"/standings/{date}")

    def get_boxscore(self, game_id: int) -> dict[str, Any]:
        return self._get(f"/gamecenter/{game_id}/boxscore")

    def get_play_by_play(self, game_id: int) -> dict[str, Any]:
        return self._get(f"/gamecenter/{game_id}/play-by-play")

    def get_shift_charts(self, game_id: int) -> dict[str, Any]:
        return self._get_url(f"{LEGACY_STATS_URL}/shiftcharts?cayenneExp=gameId={game_id}")

    def get_right_rail(self, game_id: int) -> dict[str, Any]:
        return self._get(f"/gamecenter/{game_id}/right-rail")

    def get_landing(self, game_id: int) -> dict[str, Any]:
        return self._get(f"/gamecenter/{game_id}/landing")
