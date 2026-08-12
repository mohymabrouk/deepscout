"""A small repository abstraction with an in-memory implementation for the MVP.

The interface is deliberately storage-neutral so a Postgres repository can replace it
without changing the API or research pipeline.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.research.models import RunMetrics, StageTiming
from app.schemas.events import RunEvent
from app.schemas.research import ResearchReport, Source, Usage

TERMINAL_STATUSES = {"completed", "failed", "limited"}


@dataclass
class RunRecord:
    id: str
    question: str
    identity_key: str
    status: str = "pending"
    report: ResearchReport | None = None
    sources: list[Source] = field(default_factory=list)
    usage: Usage | None = None
    search_calls: int = 0
    error_code: str | None = None
    events: list[RunEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metrics: RunMetrics = field(init=False)

    def __post_init__(self) -> None:
        self.metrics = RunMetrics(started_at=self.created_at)


class InMemoryRunRepository:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, question: str, identity_key: str) -> RunRecord:
        record = RunRecord(id=f"run_{uuid4().hex}", question=question, identity_key=identity_key)
        async with self._lock:
            self._runs[record.id] = record
        return record

    async def get(self, run_id: str) -> RunRecord | None:
        async with self._lock:
            return self._runs.get(run_id)

    async def update_status(self, run_id: str, status: str) -> None:
        async with self._lock:
            self._runs[run_id].status = status

    async def append_event(self, run_id: str, event: RunEvent) -> None:
        async with self._lock:
            self._runs[run_id].events.append(event)

    async def complete(
        self, run_id: str, report: ResearchReport, sources: list[Source], usage: Usage
    ) -> None:
        async with self._lock:
            run = self._runs[run_id]
            run.status = "completed"
            run.report = report
            run.sources = sources
            run.usage = usage

    async def increment_search_calls(self, run_id: str) -> None:
        async with self._lock:
            self._runs[run_id].search_calls += 1
            self._runs[run_id].metrics.search_calls += 1

    async def set_fetch_counts(self, run_id: str, attempted: int, succeeded: int) -> None:
        async with self._lock:
            metrics = self._runs[run_id].metrics
            metrics.pages_attempted = max(0, attempted)
            metrics.pages_succeeded = max(0, succeeded)

    async def record_stage(self, run_id: str, stage: str, started_at: datetime, completed_at: datetime, status: str = "completed") -> None:
        async with self._lock:
            self._runs[run_id].metrics.stage_timings.append(
                StageTiming(
                    stage=stage,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=(completed_at - started_at).total_seconds() * 1000,
                    status="failed" if status == "failed" else "completed",
                )
            )

    async def finalize_metrics(self, run_id: str, completed_at: datetime, budget) -> None:
        async with self._lock:
            metrics = self._runs[run_id].metrics
            metrics.completed_at = completed_at
            metrics.provider_names = list(budget.provider_names)
            metrics.fallback_used = budget.fallback_used

    async def fail(self, run_id: str, status: str, error_code: str) -> None:
        async with self._lock:
            self._runs[run_id].status = status
            self._runs[run_id].error_code = error_code

    async def list_events(self, run_id: str, offset: int = 0) -> list[RunEvent]:
        async with self._lock:
            return list(self._runs[run_id].events[offset:])

    async def all_for_identity(self, identity_key: str) -> list[RunRecord]:
        async with self._lock:
            return [run for run in self._runs.values() if run.identity_key == identity_key]
