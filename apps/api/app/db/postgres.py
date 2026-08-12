from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.core.errors import IDEMPOTENCY_CONFLICT, DomainError
from app.db.repository import DocumentRecord, RunRecord
from app.research.models import EvidencePassage, RunMetrics, StageTiming
from app.schemas.events import RunEvent
from app.schemas.research import ResearchReport, Source, SourceQuality, Usage


class PostgresRunRepository:
    """Postgres-backed implementation of the run repository contract.

    Database access stays behind FastAPI; the browser never receives a service-role
    credential and ownership is checked in every query that exposes a run.
    """

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
                        dsn=self.database_url, min_size=1, max_size=10, command_timeout=30
                    )
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def ready(self) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            await connection.fetchval("select 1")
        return True

    async def recover_incomplete_runs(self) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                rows = await connection.fetch(
                    """
                    update research_runs
                    set status = 'failed', stage = 'failed',
                        error_code = 'API_RESTARTED', completed_at = now()
                    where status not in ('completed', 'failed', 'limited')
                    returning id
                    """
                )
                if rows:
                    await connection.executemany(
                        """
                        insert into run_events (run_id, event_type, payload)
                        values ($1, 'error', $2::jsonb)
                        """,
                        [(row["id"], '{"code":"API_RESTARTED"}') for row in rows],
                    )

    async def create_document(
        self,
        filename: str,
        extracted_text: str,
        page_count: int,
        content_hash: str,
        identity_key: str,
        user_id: str | None = None,
    ) -> DocumentRecord:
        pool = await self._get_pool()
        document_id = uuid4()
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                insert into user_documents
                    (id, user_id, anonymous_key, filename, extracted_text, page_count, content_hash)
                values ($1, $2, $3, $4, $5, $6, $7)
                returning *
                """,
                document_id,
                UUID(user_id) if user_id else None,
                identity_key if user_id is None else None,
                filename,
                extracted_text,
                page_count,
                content_hash,
            )
        return DocumentRecord(
            id=str(row["id"]),
            filename=row["filename"],
            extracted_text=row["extracted_text"],
            page_count=row["page_count"],
            content_hash=row["content_hash"],
            identity_key=row["anonymous_key"] or "",
            user_id=str(row["user_id"]) if row["user_id"] else None,
            created_at=row["created_at"],
        )

    async def get_owned_documents(
        self, document_ids: list[str], identity_key: str, user_id: str | None
    ) -> list[DocumentRecord]:
        if not document_ids:
            return []
        parsed_ids: list[UUID] = []
        try:
            parsed_ids = [UUID(document_id) for document_id in document_ids]
        except ValueError:
            return []
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            if user_id:
                rows = await connection.fetch(
                    """
                    select * from user_documents
                    where id = any($1::uuid[]) and user_id = $2
                    order by array_position($1::uuid[], id)
                    """,
                    parsed_ids,
                    UUID(user_id),
                )
            else:
                rows = await connection.fetch(
                    """
                    select * from user_documents
                    where id = any($1::uuid[]) and user_id is null and anonymous_key = $2
                    order by array_position($1::uuid[], id)
                    """,
                    parsed_ids,
                    identity_key,
                )
        if len(rows) != len(parsed_ids):
            return []
        return [
            DocumentRecord(
                id=str(row["id"]),
                filename=row["filename"],
                extracted_text=row["extracted_text"],
                page_count=row["page_count"],
                content_hash=row["content_hash"],
                identity_key=row["anonymous_key"] or "",
                user_id=str(row["user_id"]) if row["user_id"] else None,
                created_at=row["created_at"],
            )
            for row in rows
        ]

    @staticmethod
    def _run_uuid(run_id: str) -> UUID | None:
        try:
            return UUID(run_id)
        except ValueError:
            return None

    @staticmethod
    def _json(value: Any) -> Any:
        if isinstance(value, str):
            return json.loads(value)
        return value

    @classmethod
    def _record(
        cls,
        row: Any,
        sources: list[Source] | None = None,
        events: list[RunEvent] | None = None,
    ) -> RunRecord:
        report_payload = cls._json(row["report"]) if row["report"] else None
        report = ResearchReport.model_validate(report_payload) if report_payload else None
        usage = None
        if row["status"] == "completed":
            usage = Usage(
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                llm_calls=row["llm_calls"],
            )
        metrics = RunMetrics(started_at=row["started_at"])
        metrics.completed_at = row["completed_at"]
        metrics.search_calls = row["search_calls"]
        metrics.pages_attempted = row["pages_attempted"]
        metrics.pages_succeeded = row["pages_succeeded"]
        metrics.provider_names = cls._json(row["provider_names"] or "[]")
        metrics.fallback_used = row["fallback_used"]
        for item in cls._json(row["stage_timings"] or "[]"):
            metrics.stage_timings.append(
                StageTiming(
                    stage=item["stage"],
                    started_at=datetime.fromisoformat(item["started_at"]),
                    completed_at=datetime.fromisoformat(item["completed_at"]),
                    duration_ms=item["duration_ms"],
                    status=item["status"],
                )
            )
        record = RunRecord(
            id=str(row["id"]),
            question=row["question"],
            identity_key=row["anonymous_key"] or "",
            user_id=str(row["user_id"]) if row["user_id"] else None,
            status=row["status"],
            report=report,
            sources=sources or [],
            source_count=row["source_count"] if "source_count" in row else len(sources or []),
            title=report.title if report else (row["report_title"] if "report_title" in row else None),
            usage=usage,
            search_calls=row["search_calls"],
            error_code=row["error_code"],
            events=events or [],
            created_at=row["created_at"],
        )
        record.metrics = metrics
        return record

    async def _load(self, row: Any) -> RunRecord:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            source_rows = await connection.fetch(
                """
                select citation_id, title, url, domain, fetched_at,
                    quality_score, quality_label, quality_reasons
                from sources where run_id = $1 order by citation_id asc nulls last
                """,
                row["id"],
            )
            event_rows = await connection.fetch(
                """
                select event_type, payload from run_events
                where run_id = $1 order by id asc
                """,
                row["id"],
            )
        sources = [
            Source(
                citation_id=source["citation_id"],
                title=source["title"] or "Untitled source",
                url=source["url"],
                domain=source["domain"],
                retrieved_at=source["fetched_at"] or row["created_at"],
                quality=SourceQuality(
                    score=float(source["quality_score"] or 0.5),
                    label=source["quality_label"] or "medium",
                    reasons=self._json(source["quality_reasons"] or "[]"),
                ),
            )
            for source in source_rows
        ]
        events = [RunEvent.model_validate(self._json(event["payload"])) for event in event_rows]
        return self._record(row, sources, events)

    async def create(
        self, question: str, identity_key: str, user_id: str | None = None
    ) -> RunRecord:
        pool = await self._get_pool()
        run_id = uuid4()
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                insert into research_runs (id, user_id, anonymous_key, question, status)
                values ($1, $2, $3, $4, 'pending')
                returning *, 0::integer as source_count
                """,
                run_id,
                UUID(user_id) if user_id else None,
                identity_key if user_id is None else None,
                question,
            )
        return self._record(row)

    async def get(self, run_id: str) -> RunRecord | None:
        parsed_id = self._run_uuid(run_id)
        if parsed_id is None:
            return None
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                "select *, (select count(*)::integer from sources s where s.run_id = research_runs.id) as source_count from research_runs where id = $1",
                parsed_id,
            )
        return await self._load(row) if row else None

    async def get_owned(
        self, run_id: str, identity_key: str, user_id: str | None
    ) -> RunRecord | None:
        parsed_id = self._run_uuid(run_id)
        if parsed_id is None:
            return None
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            if user_id:
                row = await connection.fetchrow(
                    "select *, (select count(*)::integer from sources s where s.run_id = research_runs.id) as source_count from research_runs where id = $1 and user_id = $2",
                    parsed_id,
                    UUID(user_id),
                )
            else:
                row = await connection.fetchrow(
                    "select *, (select count(*)::integer from sources s where s.run_id = research_runs.id) as source_count from research_runs where id = $1 and user_id is null and anonymous_key = $2",
                    parsed_id,
                    identity_key,
                )
        return await self._load(row) if row else None

    async def update_status(self, run_id: str, status: str) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                "update research_runs set status = $2, stage = $2 where id = $1",
                UUID(run_id),
                status,
            )

    async def append_event(self, run_id: str, event: RunEvent) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                "insert into run_events (run_id, event_type, stage, payload) values ($1, $2, $3, $4::jsonb)",
                UUID(run_id),
                event.event,
                event.stage,
                json.dumps(event.model_dump(mode="json")),
            )

    async def complete(
        self,
        run_id: str,
        report: ResearchReport,
        sources: list[Source],
        usage: Usage,
        evidence: list[EvidencePassage] | None = None,
    ) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    update research_runs
                    set status = 'completed', stage = 'completed', report = $2::jsonb,
                        input_tokens = $3, output_tokens = $4, llm_calls = $5
                    where id = $1
                    """,
                    UUID(run_id),
                    json.dumps(report.model_dump(mode="json")),
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.llm_calls,
                )
                await connection.execute("delete from sources where run_id = $1", UUID(run_id))
                await connection.executemany(
                    """
                    insert into sources (
                        run_id, citation_id, url, canonical_url, domain, title, fetched_at,
                        fetch_status, quality_score, quality_label, quality_reasons
                    )
                    values ($1, $2, $3, $3, $4, $5, $6, 'succeeded', $7, $8, $9::jsonb)
                    """,
                    [
                        (
                            UUID(run_id),
                            source.citation_id,
                            source.url,
                            source.domain,
                            source.title,
                            source.retrieved_at,
                            source.quality.score,
                            source.quality.label,
                            json.dumps(source.quality.reasons),
                        )
                        for source in sources
                    ],
                )
                await connection.execute(
                    "delete from evidence_passages where run_id = $1", UUID(run_id)
                )
                if evidence:
                    source_rows = await connection.fetch(
                        "select id, citation_id from sources where run_id = $1",
                        UUID(run_id),
                    )
                    source_ids = {
                        row["citation_id"]: row["id"] for row in source_rows
                    }
                    await connection.executemany(
                        """
                        insert into evidence_passages
                            (run_id, source_id, citation_id, excerpt, relevance_score)
                        values ($1, $2, $3, $4, $5)
                        """,
                        [
                            (
                                UUID(run_id),
                                source_ids.get(citation_id),
                                citation_id,
                                item.excerpt,
                                item.relevance_score,
                            )
                            for citation_id, item in enumerate(evidence, start=1)
                        ],
                    )

    async def increment_search_calls(self, run_id: str) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                "update research_runs set search_calls = search_calls + 1 where id = $1",
                UUID(run_id),
            )

    async def set_fetch_counts(self, run_id: str, attempted: int, succeeded: int) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                "update research_runs set pages_attempted = $2, pages_succeeded = $3 where id = $1",
                UUID(run_id),
                max(0, attempted),
                max(0, succeeded),
            )

    async def record_stage(
        self,
        run_id: str,
        stage: str,
        started_at: datetime,
        completed_at: datetime,
        status: str = "completed",
    ) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                "select stage_timings from research_runs where id = $1", UUID(run_id)
            )
            timings = self._json(row["stage_timings"] or "[]") if row else []
            timings.append(
                {
                    "stage": stage,
                    "started_at": started_at.isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "duration_ms": (completed_at - started_at).total_seconds() * 1000,
                    "status": "failed" if status == "failed" else "completed",
                }
            )
            await connection.execute(
                "update research_runs set stage_timings = $2::jsonb where id = $1",
                UUID(run_id),
                json.dumps(timings),
            )

    async def finalize_metrics(self, run_id: str, completed_at: datetime, budget) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                """
                update research_runs set completed_at = $2, provider_names = $3::jsonb,
                    fallback_used = $4 where id = $1
                """,
                UUID(run_id),
                completed_at,
                json.dumps(list(budget.provider_names)),
                budget.fallback_used,
            )

    async def fail(self, run_id: str, status: str, error_code: str) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                "update research_runs set status = $2, error_code = $3, completed_at = now() where id = $1",
                UUID(run_id),
                status,
                error_code,
            )

    async def list_events(self, run_id: str, offset: int = 0) -> list[RunEvent]:
        parsed_id = self._run_uuid(run_id)
        if parsed_id is None:
            return []
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                "select payload from run_events where run_id = $1 order by id asc offset $2",
                parsed_id,
                offset,
            )
        return [RunEvent.model_validate(self._json(row["payload"])) for row in rows]

    async def list_for_user(
        self,
        user_id: str,
        limit: int,
        before: tuple[datetime, str] | None = None,
    ) -> tuple[list[RunRecord], tuple[datetime, str] | None]:
        pool = await self._get_pool()
        query = """
            select r.*, r.report ->> 'title' as report_title,
              (select count(*)::integer from sources s where s.run_id = r.id) as source_count
            from research_runs r where r.user_id = $1
        """
        args: list[Any] = [UUID(user_id)]
        if before:
            query += " and (r.created_at < $2 or (r.created_at = $2 and r.id < $3))"
            args.extend([before[0], UUID(before[1])])
        query += f" order by r.created_at desc, r.id desc limit ${len(args) + 1}"
        args.append(limit + 1)
        async with pool.acquire() as connection:
            rows = await connection.fetch(query, *args)
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        records = [self._record(row) for row in page_rows]
        next_before = (
            (page_rows[-1]["created_at"], str(page_rows[-1]["id"]))
            if has_more and page_rows
            else None
        )
        return records, next_before

    async def delete_owned(
        self, run_id: str, identity_key: str, user_id: str | None
    ) -> bool:
        parsed_id = self._run_uuid(run_id)
        if parsed_id is None:
            return False
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            if user_id:
                result = await connection.execute(
                    "delete from research_runs where id = $1 and user_id = $2",
                    parsed_id,
                    UUID(user_id),
                )
            else:
                result = await connection.execute(
                    "delete from research_runs where id = $1 and user_id is null and anonymous_key = $2",
                    parsed_id,
                    identity_key,
                )
        return result.endswith("1")

    async def get_idempotency(self, identity_key: str, idempotency_key: str) -> str | None:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                "select run_id from idempotency_keys where identity_key = $1 and idempotency_key = $2",
                identity_key,
                idempotency_key,
            )
        return str(row["run_id"]) if row else None

    async def save_idempotency(
        self, identity_key: str, idempotency_key: str, run_id: str
    ) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                """
                insert into idempotency_keys (identity_key, idempotency_key, run_id)
                values ($1, $2, $3) on conflict (identity_key, idempotency_key) do nothing
                """,
                identity_key,
                idempotency_key,
                UUID(run_id),
            )

    async def get_or_create_idempotent(
        self,
        question: str | None,
        identity_key: str,
        user_id: str | None,
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[RunRecord, bool]:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                run_id = uuid4()
                row = await connection.fetchrow(
                    """
                    insert into research_runs (id, user_id, anonymous_key, question, status)
                    values ($1, $2, $3, $4, 'pending')
                    on conflict do nothing
                    returning *, 0::integer as source_count
                    """,
                    run_id,
                    UUID(user_id) if user_id else None,
                    identity_key if user_id is None else None,
                    question,
                )
                if row is not None:
                    claimed = await connection.fetchrow(
                        """
                        insert into idempotency_keys
                            (identity_key, idempotency_key, run_id, request_hash)
                        values ($1, $2, $3, $4)
                        on conflict (identity_key, idempotency_key) do nothing
                        returning run_id
                        """,
                        identity_key,
                        idempotency_key,
                        run_id,
                        request_hash,
                    )
                    if claimed is not None:
                        return self._record(row), True
                    await connection.execute(
                        "delete from research_runs where id = $1", run_id
                    )
                existing = await connection.fetchrow(
                    """
                    select r.*, 0::integer as source_count, i.request_hash
                    from idempotency_keys i
                    join research_runs r on r.id = i.run_id
                    where i.identity_key = $1 and i.idempotency_key = $2
                    """,
                    identity_key,
                    idempotency_key,
                )
                if existing is None:
                    raise RuntimeError("Idempotency claim disappeared during transaction")
                if existing["request_hash"] and existing["request_hash"] != request_hash:
                    raise DomainError(
                        IDEMPOTENCY_CONFLICT,
                        "The idempotency key was already used for a different request.",
                        409,
                    )
                return self._record(existing), False
