"""
Shared Brave Search API rate limiter.

Module-level singleton that enforces per-second request limits across all
tools that call the Brave Search API (brave_web_search).
Thread-safe for future-proofing.

Note: Legal risk analysis (trademarks/patents) now uses Gemini Deep Research
instead of Brave Search. This rate limiter is only used by BraveWebSearchTool
(GAC/policy research).

Configuration (env vars):
    BRAVE_RATE_LIMIT_RPS    — requests per second (default 1 for Free plan)
    BRAVE_RATE_LIMIT_MONTHLY — monthly quota     (default 2000 for Free plan)
"""

import logging
import os
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class BraveRateLimiter:
    """Token-bucket-style rate limiter for the Brave Search API."""

    def __init__(
        self,
        requests_per_second: float = 1.0,
        monthly_quota: int = 2000,
    ):
        self._rps = requests_per_second
        self._min_interval = 1.0 / requests_per_second
        self._monthly_quota = monthly_quota

        self._lock = threading.Lock()
        self._last_request_time: float = 0.0
        self._request_count: int = 0
        self._quota_exhausted: bool = False
        self._consecutive_429s: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def quota_exhausted(self) -> bool:
        return self._quota_exhausted

    def mark_quota_exhausted(self) -> None:
        """Mark the API quota as exhausted for the rest of this process."""
        self._quota_exhausted = True
        logger.warning("Brave API quota marked as exhausted for this session")

    def wait_for_slot(self) -> bool:
        """Block until a request slot is available.

        Returns ``True`` if a slot was acquired, ``False`` if the quota has
        been exhausted (callers should fall through to Firecrawl / model
        knowledge).
        """
        if self._quota_exhausted:
            return False

        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_request_time = time.monotonic()
            self._request_count += 1
            return True

    def record_429(self, retry_after: Optional[float] = None) -> float:
        """Record a 429 response and return the recommended wait time.

        Args:
            retry_after: Value from the ``Retry-After`` header (seconds),
                         or ``None`` if the header was absent.

        Returns:
            Seconds to sleep before the next retry.
        """
        with self._lock:
            self._consecutive_429s += 1

            if retry_after is not None and retry_after > 0:
                return retry_after

            # Exponential backoff: 2 s → 4 s → 8 s … capped at 30 s
            return float(min(2 ** self._consecutive_429s, 30))

    def record_success(self) -> None:
        """Record a successful (non-429) response."""
        with self._lock:
            self._consecutive_429s = 0

    def get_stats(self) -> dict:
        """Snapshot for audit / diagnostic logging."""
        return {
            "requests_this_session": self._request_count,
            "quota_exhausted": self._quota_exhausted,
            "consecutive_429s": self._consecutive_429s,
            "configured_rps": self._rps,
            "configured_monthly_quota": self._monthly_quota,
        }


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_instance: Optional[BraveRateLimiter] = None
_instance_lock = threading.Lock()


def get_brave_rate_limiter() -> BraveRateLimiter:
    """Return (and lazily create) the global Brave rate-limiter singleton."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:  # double-checked locking
                rps = float(os.getenv("BRAVE_RATE_LIMIT_RPS", "1.0"))
                monthly = int(os.getenv("BRAVE_RATE_LIMIT_MONTHLY", "2000"))
                _instance = BraveRateLimiter(
                    requests_per_second=rps,
                    monthly_quota=monthly,
                )
                logger.info(
                    f"Brave rate limiter initialized: {rps} req/s, "
                    f"{monthly} monthly quota"
                )
    return _instance
