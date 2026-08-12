from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from app.core.errors import CONCURRENCY_LIMIT, DAILY_RUN_LIMIT, DomainError


@dataclass
class _Window:
    number: int
    count: int = 0


class FixedWindowRateLimiter:
    """Single-process fixed-window limiter suitable for the documented MVP topology."""

    def __init__(self, window_seconds: int = 60) -> None:
        self.window_seconds = window_seconds
        self._windows: dict[str, _Window] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int, now: float | None = None) -> tuple[bool, int, int]:
        timestamp = now if now is not None else datetime.now(UTC).timestamp()
        number = int(timestamp // self.window_seconds)
        reset_at = (number + 1) * self.window_seconds
        async with self._lock:
            self._windows = {
                identity: item
                for identity, item in self._windows.items()
                if item.number >= number - 1
            }
            window = self._windows.get(key)
            if window is None or window.number != number:
                window = _Window(number)
                self._windows[key] = window
            allowed = window.count < limit
            if allowed:
                window.count += 1
            return allowed, max(0, limit - window.count), max(1, int(reset_at - timestamp))


@dataclass
class _DailyUsage:
    runs_used: int = 0
    active_runs: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    llm_calls: int = 0
    search_calls: int = 0


class RunQuotaService:
    """Atomic in-memory reservations for a single API process.

    The interface maps directly to the documented usage_daily atomic SQL operation;
    a Postgres implementation can replace this class without changing routes.
    """

    def __init__(self) -> None:
        self._usage: dict[tuple[str, date], _DailyUsage] = {}
        self._active_runs: dict[str, int] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _today() -> date:
        return datetime.now(UTC).date()

    async def reserve_run(self, identity: str, daily_limit: int, concurrency_limit: int) -> None:
        today = self._today()
        async with self._lock:
            self._usage = {
                key: value for key, value in self._usage.items() if key[1] >= today
            }
            usage = self._usage.setdefault((identity, today), _DailyUsage())
            if usage.runs_used >= daily_limit:
                raise DomainError(
                    DAILY_RUN_LIMIT,
                    "Daily demo run limit reached.",
                    429,
                    retry_after_seconds=self.seconds_until_reset(),
                )
            if self._active_runs.get(identity, 0) >= concurrency_limit:
                raise DomainError(
                    CONCURRENCY_LIMIT,
                    "The maximum number of active research runs has been reached.",
                    429,
                    retry_after_seconds=5,
                )
            usage.runs_used += 1
            usage.active_runs += 1
            self._active_runs[identity] = self._active_runs.get(identity, 0) + 1

    async def finish_run(self, identity: str, input_tokens: int = 0, output_tokens: int = 0, llm_calls: int = 0, search_calls: int = 0) -> None:
        today = self._today()
        async with self._lock:
            usage = self._usage.setdefault((identity, today), _DailyUsage())
            usage.active_runs = max(0, usage.active_runs - 1)
            active = max(0, self._active_runs.get(identity, 0) - 1)
            if active:
                self._active_runs[identity] = active
            else:
                self._active_runs.pop(identity, None)
            usage.input_tokens += max(0, input_tokens)
            usage.output_tokens += max(0, output_tokens)
            usage.llm_calls += max(0, llm_calls)
            usage.search_calls += max(0, search_calls)

    async def get(self, identity: str) -> _DailyUsage:
        today = self._today()
        async with self._lock:
            usage = self._usage.get((identity, today), _DailyUsage())
            return _DailyUsage(**usage.__dict__)

    @staticmethod
    def seconds_until_reset() -> int:
        now = datetime.now(UTC)
        tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
        return max(1, int((tomorrow - now).total_seconds()))
