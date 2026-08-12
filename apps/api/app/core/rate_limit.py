from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

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


class PostgresFixedWindowRateLimiter:
    """Cross-process fixed-window limiter backed by an atomic row lock."""

    def __init__(self, database_url: str, window_seconds: int = 60) -> None:
        self.database_url = database_url
        self.window_seconds = window_seconds
        self._pool: Any = None
        self._pool_lock = asyncio.Lock()

    async def _get_pool(self):
        if self._pool is None:
            async with self._pool_lock:
                if self._pool is None:
                    import asyncpg

                    self._pool = await asyncpg.create_pool(
                        dsn=self.database_url, min_size=1, max_size=10, command_timeout=10
                    )
        return self._pool

    async def check(self, key: str, limit: int, now: float | None = None) -> tuple[bool, int, int]:
        timestamp = now if now is not None else datetime.now(UTC).timestamp()
        window_number = int(timestamp // self.window_seconds)
        window_started_at = datetime.fromtimestamp(
            window_number * self.window_seconds, tz=UTC
        )
        reset_after = max(1, int((window_number + 1) * self.window_seconds - timestamp))
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    insert into request_rate_windows
                        (identity_key, window_started_at, request_count)
                    values ($1, $2, 0)
                    on conflict (identity_key) do nothing
                    """,
                    key,
                    window_started_at,
                )
                row = await connection.fetchrow(
                    """
                    select window_started_at, request_count
                    from request_rate_windows
                    where identity_key = $1
                    for update
                    """,
                    key,
                )
                if row["window_started_at"] != window_started_at:
                    count = 0
                    await connection.execute(
                        """
                        update request_rate_windows
                        set window_started_at = $2, request_count = 1, updated_at = now()
                        where identity_key = $1
                        """,
                        key,
                        window_started_at,
                    )
                    return True, max(0, limit - 1), reset_after
                count = int(row["request_count"])
                if count >= limit:
                    return False, 0, reset_after
                await connection.execute(
                    """
                    update request_rate_windows
                    set request_count = request_count + 1, updated_at = now()
                    where identity_key = $1
                    """,
                    key,
                )
                return True, max(0, limit - count - 1), reset_after

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


class PostgresRunQuotaService:
    """Persistent daily quota and active-run reservations."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._pool: Any = None
        self._pool_lock = asyncio.Lock()

    async def _get_pool(self):
        if self._pool is None:
            async with self._pool_lock:
                if self._pool is None:
                    import asyncpg

                    self._pool = await asyncpg.create_pool(
                        dsn=self.database_url, min_size=1, max_size=10, command_timeout=10
                    )
        return self._pool

    async def reserve_run(self, identity: str, daily_limit: int, concurrency_limit: int) -> None:
        today = datetime.now(UTC).date()
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    insert into usage_daily (identity_key, usage_date)
                    values ($1, $2)
                    on conflict (identity_key, usage_date) do nothing
                    """,
                    identity,
                    today,
                )
                row = await connection.fetchrow(
                    """
                    select research_runs, active_runs
                    from usage_daily
                    where identity_key = $1 and usage_date = $2
                    for update
                    """,
                    identity,
                    today,
                )
                if row["research_runs"] >= daily_limit:
                    raise DomainError(
                        DAILY_RUN_LIMIT,
                        "Daily demo run limit reached.",
                        429,
                        retry_after_seconds=RunQuotaService.seconds_until_reset(),
                    )
                if row["active_runs"] >= concurrency_limit:
                    raise DomainError(
                        CONCURRENCY_LIMIT,
                        "The maximum number of active research runs has been reached.",
                        429,
                        retry_after_seconds=5,
                    )
                await connection.execute(
                    """
                    update usage_daily
                    set research_runs = research_runs + 1,
                        active_runs = active_runs + 1
                    where identity_key = $1 and usage_date = $2
                    """,
                    identity,
                    today,
                )

    async def finish_run(
        self,
        identity: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        llm_calls: int = 0,
        search_calls: int = 0,
    ) -> None:
        today = datetime.now(UTC).date()
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                """
                insert into usage_daily (
                    identity_key, usage_date, active_runs,
                    input_tokens, output_tokens, llm_calls, search_calls
                )
                values ($1, $2, 0, $3, $4, $5, $6)
                on conflict (identity_key, usage_date) do update set
                    active_runs = greatest(0, usage_daily.active_runs - 1),
                    input_tokens = usage_daily.input_tokens + excluded.input_tokens,
                    output_tokens = usage_daily.output_tokens + excluded.output_tokens,
                    llm_calls = usage_daily.llm_calls + excluded.llm_calls,
                    search_calls = usage_daily.search_calls + excluded.search_calls
                """,
                identity,
                today,
                max(0, input_tokens),
                max(0, output_tokens),
                max(0, llm_calls),
                max(0, search_calls),
            )

    async def get(self, identity: str) -> _DailyUsage:
        today = datetime.now(UTC).date()
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                select research_runs, active_runs, input_tokens, output_tokens,
                       llm_calls, search_calls
                from usage_daily
                where identity_key = $1 and usage_date = $2
                """,
                identity,
                today,
            )
        if row is None:
            return _DailyUsage()
        return _DailyUsage(
            runs_used=row["research_runs"],
            active_runs=row["active_runs"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            llm_calls=row["llm_calls"],
            search_calls=row["search_calls"],
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
