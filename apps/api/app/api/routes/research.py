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


async def _execute(request: Request, run_id: str, question: str) -> None:
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
        request.app.state.tasks.discard(asyncio.current_task())


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
    identity_key = request.headers.get(
        "Authorization", "anon:" + (request.client.host if request.client else "unknown")
    )
    if idempotency_key:
        existing = getattr(request.app.state, "idempotency", {}).get(
            (identity_key, idempotency_key)
        )
        if existing:
            return ResearchAccepted(
                run_id=existing, status="pending", events_url=f"/v1/research/{existing}/events"
            )
    record = await request.app.state.repository.create(body.question, identity_key)
    if not hasattr(request.app.state, "idempotency"):
        request.app.state.idempotency = {}
    if idempotency_key:
        request.app.state.idempotency[(identity_key, idempotency_key)] = record.id
    task = asyncio.create_task(_execute(request, record.id, body.question))
    request.app.state.tasks.add(task)
    return ResearchAccepted(
        run_id=record.id, status="pending", events_url=f"/v1/research/{record.id}/events"
    )


@router.get("/{run_id}", response_model=ResearchResult)
async def get_research(request: Request, run_id: str) -> ResearchResult:
    record = await request.app.state.repository.get(run_id)
    if record is None:
        raise DomainError(RUN_NOT_FOUND, "Research run not found.", 404)
    return _result(record)


def _sse(event: RunEvent) -> str:
    return f"event: {event.event}\ndata: {json.dumps(event.model_dump(mode='json'))}\n\n"


@router.get("/{run_id}/events")
async def research_events(request: Request, run_id: str) -> StreamingResponse:
    record = await request.app.state.repository.get(run_id)
    if record is None:
        raise DomainError(RUN_NOT_FOUND, "Research run not found.", 404)

    async def stream() -> AsyncIterator[str]:
        offset = 0
        while True:
            current = await request.app.state.repository.get(run_id)
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
