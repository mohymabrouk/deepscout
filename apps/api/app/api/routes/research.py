from __future__ import annotations

import asyncio
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


async def _execute(request: Request, run_id: str, question: str, identity_key: str) -> None:
    try:
        await asyncio.wait_for(
            request.app.state.orchestrator.run(run_id, question),
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
    if idempotency_key:
        existing = await request.app.state.repository.get_idempotency(identity_key, idempotency_key)
        if existing:
            record = await request.app.state.repository.get_owned(
                existing, identity_key, request.state.user_id
            )
            if record:
                return ResearchAccepted(
                    run_id=existing, status="pending", events_url=f"/v1/research/{existing}/events"
                )
    await request.app.state.quota_service.reserve_run(
        identity_key,
        request.app.state.settings.auth_runs_per_day if authenticated else request.app.state.settings.anon_runs_per_day,
        request.app.state.settings.auth_concurrent_runs if authenticated else request.app.state.settings.anon_concurrent_runs,
    )
    record = await request.app.state.repository.create(
        body.question, identity_key, request.state.user_id
    )
    if idempotency_key:
        await request.app.state.repository.save_idempotency(identity_key, idempotency_key, record.id)
    task = asyncio.create_task(_execute(request, record.id, body.question, identity_key))
    request.app.state.tasks.add(task)
    request.app.state.run_tasks[record.id] = task
    return ResearchAccepted(
        run_id=record.id, status="pending", events_url=f"/v1/research/{record.id}/events"
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
