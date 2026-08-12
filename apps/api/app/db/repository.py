"""Run storage contracts and the local in-memory implementation.

The API only accesses runs through ownership-aware repository methods. The in-memory
implementation keeps local development infrastructure-free while the same contract is
used by the Postgres adapter when ``DATABASE_URL`` is configured.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.core.errors import IDEMPOTENCY_CONFLICT, DomainError
from app.research.models import EvidencePassage, RunMetrics, StageTiming
from app.schemas.events import RunEvent
from app.schemas.research import ResearchReport, Source, Usage

TERMINAL_STATUSES = {"completed", "failed", "limited"}


@dataclass
class RunRecord:
    id: str
    question: str | None
    identity_key: str
    user_id: str | None = None
    status: str = "pending"
    report: ResearchReport | None = None
    sources: list[Source] = field(default_factory=list)
    source_count: int = 0
    title: str | None = None
    usage: Usage | None = None
    search_calls: int = 0
    error_code: str | None = None
    events: list[RunEvent] = field(default_factory=list)
    evidence_passages: list[EvidencePassage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metrics: RunMetrics = field(init=False)

    def __post_init__(self) -> None:
        self.metrics = RunMetrics(started_at=self.created_at)


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    filename: str
    extracted_text: str
    page_count: int
    content_hash: str
    identity_key: str
    user_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class InMemoryRunRepository:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._documents: dict[str, DocumentRecord] = {}
        self._idempotency: dict[tuple[str, str], tuple[str, str]] = {}
        self._lock = asyncio.Lock()

    async def create(
        self, question: str, identity_key: str, user_id: str | None = None
    ) -> RunRecord:
        record = RunRecord(
            id=str(uuid4()), question=question, identity_key=identity_key, user_id=user_id
        )
        async with self._lock:
            self._runs[record.id] = record
        return record

    async def get(self, run_id: str) -> RunRecord | None:
        async with self._lock:
            return self._runs.get(run_id)

    @staticmethod
    def _owns(record: RunRecord, identity_key: str, user_id: str | None) -> bool:
        if user_id is not None:
            return record.user_id == user_id
        return record.user_id is None and record.identity_key == identity_key

    async def get_owned(
        self, run_id: str, identity_key: str, user_id: str | None
    ) -> RunRecord | None:
        async with self._lock:
            record = self._runs.get(run_id)
            if record is None or not self._owns(record, identity_key, user_id):
                return None
            return record

    async def update_status(self, run_id: str, status: str) -> None:
        async with self._lock:
            self._runs[run_id].status = status

    async def append_event(self, run_id: str, event: RunEvent) -> None:
        async with self._lock:
            self._runs[run_id].events.append(event)

    async def complete(
        self,
        run_id: str,
        report: ResearchReport,
        sources: list[Source],
        usage: Usage,
        evidence: list[EvidencePassage] | None = None,
    ) -> None:
        async with self._lock:
            run = self._runs[run_id]
            run.status = "completed"
            run.report = report
            run.sources = sources
            run.source_count = len(sources)
            run.title = report.title
            run.usage = usage
            run.evidence_passages = list(evidence or [])

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

    async def list_for_user(
        self,
        user_id: str,
        limit: int,
        before: tuple[datetime, str] | None = None,
    ) -> tuple[list[RunRecord], tuple[datetime, str] | None]:
        async with self._lock:
            runs = sorted(
                (run for run in self._runs.values() if run.user_id == user_id),
                key=lambda run: (run.created_at, run.id),
                reverse=True,
            )
            if before is not None:
                runs = [
                    run
                    for run in runs
                    if (run.created_at, run.id) < before
                ]
            page = runs[:limit]
            has_more = len(runs) > limit
            next_before = (page[-1].created_at, page[-1].id) if has_more and page else None
            return page, next_before

    async def delete_owned(
        self, run_id: str, identity_key: str, user_id: str | None
    ) -> bool:
        async with self._lock:
            record = self._runs.get(run_id)
            if record is None or not self._owns(record, identity_key, user_id):
                return False
            del self._runs[run_id]
            return True

    async def get_idempotency(self, identity_key: str, idempotency_key: str) -> str | None:
        async with self._lock:
            item = self._idempotency.get((identity_key, idempotency_key))
            return item[0] if item else None

    async def save_idempotency(
        self, identity_key: str, idempotency_key: str, run_id: str
    ) -> None:
        async with self._lock:
            self._idempotency.setdefault((identity_key, idempotency_key), (run_id, ""))

    async def get_or_create_idempotent(
        self,
        question: str | None,
        identity_key: str,
        user_id: str | None,
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[RunRecord, bool]:
        async with self._lock:
            key = (identity_key, idempotency_key)
            existing = self._idempotency.get(key)
            if existing is not None:
                existing_run_id, existing_hash = existing
                if existing_hash and existing_hash != request_hash:
                    raise DomainError(
                        IDEMPOTENCY_CONFLICT,
                        "The idempotency key was already used for a different request.",
                        409,
                    )
                record = self._runs.get(existing_run_id)
                if record is not None:
                    return record, False
                self._idempotency.pop(key, None)
            record = RunRecord(
                id=str(uuid4()),
                question=question,
                identity_key=identity_key,
                user_id=user_id,
            )
            self._runs[record.id] = record
            self._idempotency[key] = (record.id, request_hash)
            return record, True

    async def ready(self) -> bool:
        return True

    async def create_document(
        self,
        filename: str,
        extracted_text: str,
        page_count: int,
        content_hash: str,
        identity_key: str,
        user_id: str | None = None,
    ) -> DocumentRecord:
        document = DocumentRecord(
            id=str(uuid4()),
            filename=filename,
            extracted_text=extracted_text,
            page_count=page_count,
            content_hash=content_hash,
            identity_key=identity_key,
            user_id=user_id,
        )
        async with self._lock:
            self._documents[document.id] = document
        return document

    async def get_owned_documents(
        self, document_ids: list[str], identity_key: str, user_id: str | None
    ) -> list[DocumentRecord]:
        async with self._lock:
            documents = [self._documents.get(document_id) for document_id in document_ids]
            if any(document is None for document in documents):
                return []
            owned = [document for document in documents if document and self._owns_document(document, identity_key, user_id)]
            return owned if len(owned) == len(document_ids) else []

    @staticmethod
    def _owns_document(document: DocumentRecord, identity_key: str, user_id: str | None) -> bool:
        if user_id is not None:
            return document.user_id == user_id
        return document.user_id is None and document.identity_key == identity_key

    async def recover_incomplete_runs(self) -> None:
        async with self._lock:
            for run in self._runs.values():
                if run.status not in TERMINAL_STATUSES:
                    run.status = "failed"
                    run.error_code = "API_RESTARTED"
                    run.events.append(RunEvent(event="error", data={"code": "API_RESTARTED"}))
