from __future__ import annotations

from fastapi import APIRouter, Query, Request, Response, status

from app.core.errors import RUN_NOT_FOUND, DomainError
from app.core.security import decode_cursor, encode_cursor
from app.schemas.research import RunListResponse, RunSummary

router = APIRouter(prefix="/v1/runs", tags=["runs"])


def _summary(record) -> RunSummary:
    return RunSummary(
        id=record.id,
        status=record.status,
        question=record.question,
        title=record.title or (record.report.title if record.report else None),
        source_count=record.source_count or len(record.sources),
        created_at=record.created_at,
        completed_at=record.metrics.completed_at,
    )


@router.get("", response_model=RunListResponse)
async def list_runs(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
) -> RunListResponse:
    user_id = request.state.user_id
    if user_id is None:
        raise DomainError("UNAUTHORIZED", "Sign in to access run history.", 401)
    before = (
        decode_cursor(cursor, request.app.state.settings.anon_id_hmac_secret)
        if cursor
        else None
    )
    records, next_before = await request.app.state.repository.list_for_user(
        user_id, limit, before
    )
    next_cursor = (
        encode_cursor(
            next_before[0], next_before[1], request.app.state.settings.anon_id_hmac_secret
        )
        if next_before
        else None
    )
    return RunListResponse(items=[_summary(record) for record in records], next_cursor=next_cursor)


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(request: Request, run_id: str) -> Response:
    deleted = await request.app.state.repository.delete_owned(
        run_id, request.state.identity_key, request.state.user_id
    )
    if not deleted:
        raise DomainError(RUN_NOT_FOUND, "Research run not found.", 404)
    task = request.app.state.run_tasks.pop(run_id, None)
    if task is not None and not task.done():
        task.cancel()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
