"""A small repository abstraction with an in-memory implementation for the MVP.

The interface is deliberately storage-neutral so a Postgres repository can replace it
without changing the API or research pipeline.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

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
