from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse

from app.core.errors import RUN_NOT_FOUND, RUN_TIMEOUT, DomainError
from app.db.repository import TERMINAL_STATUSES
from app.schemas.events import RunEvent
from app.schemas.research import ResearchAccepted, ResearchRequest, ResearchResult

router = APIRouter(prefix="/v1/research", tags=["research"])


def _result(record) -> ResearchResult:
    return ResearchResult(
        id=record.id,
        status=record.status,
        question=record.question,
        report=record.report,
        sources=record.sources,
        usage=record.usage,
        error_code=record.error_code,
    )


async def _execute(
    request: Request,
    run_id: str,
    question: str,
    identity_key: str,
    document_ids: list[str],
) -> None:
    try:
        documents = await request.app.state.repository.get_owned_documents(
            document_ids, identity_key, request.state.user_id
        )
        await asyncio.wait_for(
            request.app.state.orchestrator.run(run_id, question, documents=documents),
            request.app.state.settings.max_run_seconds,
        )
    except TimeoutError:
        await request.app.state.repository.fail(run_id, "failed", RUN_TIMEOUT)
        await request.app.state.repository.append_event(
            run_id, RunEvent(event="error", data={"code": RUN_TIMEOUT})
        )
    finally:
        record = await request.app.state.repository.get(run_id)
        usage = record.usage if record else None
        await request.app.state.quota_service.finish_run(
            identity_key,
            usage.input_tokens if usage else 0,
            usage.output_tokens if usage else 0,
            usage.llm_calls if usage else 0,
            record.search_calls if record else 0,
        )
        request.app.state.tasks.discard(asyncio.current_task())
        request.app.state.run_tasks.pop(run_id, None)


@router.post("", response_model=ResearchAccepted, status_code=202)
async def create_research(
    request: Request,
    body: ResearchRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ResearchAccepted:
    if len(body.question) > request.app.state.settings.max_question_chars:
        raise DomainError(
            "QUESTION_TOO_LONG", "Question exceeds the configured character limit.", 400
        )
    identity_key = request.state.identity_key
    authenticated = request.state.authenticated
    if idempotency_key is not None:
        if not idempotency_key or len(idempotency_key) > 200 or any(
            ord(char) < 33 or ord(char) > 126 for char in idempotency_key
        ):
            raise DomainError(
                "INVALID_REQUEST", "Idempotency-Key must be a printable value up to 200 characters.", 400
            )
    request_hash = hashlib.sha256(
        json.dumps(body.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if len(body.document_ids) > request.app.state.settings.max_documents_per_run:
        raise DomainError(
            "DOCUMENT_LIMIT_EXCEEDED",
            "The research run exceeds the configured document limit.",
            400,
        )
    documents = await request.app.state.repository.get_owned_documents(
        body.document_ids, identity_key, request.state.user_id
    )
    if len(documents) != len(body.document_ids):
        raise DomainError("DOCUMENT_NOT_FOUND", "One or more uploaded documents were not found.", 404)
    stored_question = body.question if request.app.state.settings.store_question_text else None
    await request.app.state.quota_service.reserve_run(
        identity_key,
        request.app.state.settings.auth_runs_per_day if authenticated else request.app.state.settings.anon_runs_per_day,
        request.app.state.settings.auth_concurrent_runs if authenticated else request.app.state.settings.anon_concurrent_runs,
    )
    if idempotency_key:
        try:
            record, created = await request.app.state.repository.get_or_create_idempotent(
                stored_question,
                identity_key,
                request.state.user_id,
                idempotency_key,
                request_hash,
            )
        except Exception:
            await request.app.state.quota_service.finish_run(identity_key)
            raise
        if not created:
            await request.app.state.quota_service.finish_run(identity_key)
            return ResearchAccepted(
                run_id=record.id,
                status=record.status,
                events_url=f"/v1/research/{record.id}/events",
            )
    else:
        record = await request.app.state.repository.create(
            stored_question, identity_key, request.state.user_id
        )
    task = asyncio.create_task(
        _execute(request, record.id, body.question, identity_key, body.document_ids)
    )
    request.app.state.tasks.add(task)
    request.app.state.run_tasks[record.id] = task
    return ResearchAccepted(
        run_id=record.id, status=record.status, events_url=f"/v1/research/{record.id}/events"
    )


@router.get("/{run_id}", response_model=ResearchResult)
async def get_research(request: Request, run_id: str) -> ResearchResult:
    record = await request.app.state.repository.get_owned(
        run_id, request.state.identity_key, request.state.user_id
    )
    if record is None:
        raise DomainError(RUN_NOT_FOUND, "Research run not found.", 404)
    return _result(record)


def _sse(event: RunEvent) -> str:
    return f"event: {event.event}\ndata: {json.dumps(event.model_dump(mode='json'))}\n\n"


@router.get("/{run_id}/events")
async def research_events(request: Request, run_id: str) -> StreamingResponse:
    record = await request.app.state.repository.get_owned(
        run_id, request.state.identity_key, request.state.user_id
    )
    if record is None:
        raise DomainError(RUN_NOT_FOUND, "Research run not found.", 404)

    async def stream() -> AsyncIterator[str]:
        offset = 0
        while True:
            current = await request.app.state.repository.get_owned(
                run_id, request.state.identity_key, request.state.user_id
            )
            if current is None:
                return
            events = await request.app.state.repository.list_events(run_id, offset)
            for event in events:
                offset += 1
                yield _sse(event)
            if current.status in TERMINAL_STATUSES and offset >= len(current.events):
                return
            await asyncio.sleep(0.1)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
