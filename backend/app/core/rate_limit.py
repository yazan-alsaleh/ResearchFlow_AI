"""In-memory fixed-window rate limiting for public run creation.

No Redis dependency by design (MVP, single-process free-tier deploy).
Limits follow PLAN.md §8.3: 3 runs/hour/IP, 10 runs/day/IP, 100 runs/day global.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

HOUR = 3600
DAY = 86400


@dataclass
class Decision:
    allowed: bool
    retry_after: int | None
    headers: dict[str, str]


class RateLimiter:
    """Fixed-window counters keyed by (bucket, window, identity)."""

    def __init__(
        self,
        *,
        per_hour: int = 3,
        per_day: int = 10,
        global_per_day: int = 100,
    ) -> None:
        self.per_hour = per_hour
        self.per_day = per_day
        self.global_per_day = global_per_day
        self._lock = threading.Lock()
        self._counts: dict[tuple[str, int, str], int] = {}

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()

    def _window(self, seconds: int, now: float) -> int:
        return int(now // seconds)

    def _bump(self, bucket: str, window: int, identity: str) -> tuple[int, int]:
        """Return (count_after_bump, limit)."""
        limits = {"hour": self.per_hour, "day": self.per_day, "global": self.global_per_day}
        key = (bucket, window, identity)
        count = self._counts.get(key, 0) + 1
        self._counts[key] = count
        return count, limits[bucket]

    def check(self, client_ip: str, now: float | None = None) -> Decision:
        moment = time.time() if now is None else now
        hour_window = self._window(HOUR, moment)
        day_window = self._window(DAY, moment)

        with self._lock:
            hour_count, hour_limit = self._bump("hour", hour_window, client_ip)
            day_count, day_limit = self._bump("day", day_window, client_ip)
            global_count, global_limit = self._bump("global", day_window, "global")

        # Remaining reflects the tightest bucket.
        remaining = max(
            0,
            min(hour_limit - hour_count, day_limit - day_count, global_limit - global_count),
        )
        headers = {
            "X-RateLimit-Limit": str(min(hour_limit, day_limit, global_limit)),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int((hour_window + 1) * HOUR)),
        }

        if hour_count > hour_limit:
            retry = int((hour_window + 1) * HOUR - moment)
            return Decision(False, retry, headers)
        if day_count > day_limit or global_count > global_limit:
            retry = int((day_window + 1) * DAY - moment)
            return Decision(False, retry, headers)
        return Decision(True, None, headers)


# Module-level limiter used by the API; configure limits from settings on import.
def build_limiter(settings) -> RateLimiter:  # type: ignore[no-untyped-def]
    return RateLimiter(
        per_hour=settings.runs_per_hour_per_ip,
        per_day=settings.runs_per_day_per_ip,
        global_per_day=settings.runs_per_day_global,
    )
