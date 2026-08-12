from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Request

from app.core.security import request_identity
from app.schemas.research import UsageResponse

router = APIRouter(prefix="/v1", tags=["usage"])


@router.get("/usage", response_model=UsageResponse)
async def usage(request: Request) -> UsageResponse:
    identity, authenticated = request_identity(
        request.headers.get("Authorization"),
        request.client.host if request.client else "unknown",
        request.app.state.settings.anon_id_hmac_secret,
    )
    current = await request.app.state.quota_service.get(identity)
    now = datetime.now(UTC)
    reset = datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    return UsageResponse(
        period="day",
        runs_used=current.runs_used,
        runs_limit=request.app.state.settings.auth_runs_per_day if authenticated else request.app.state.settings.anon_runs_per_day,
        input_tokens_used=current.input_tokens,
        input_tokens_limit=request.app.state.settings.max_input_tokens_per_run * (request.app.state.settings.auth_runs_per_day if authenticated else request.app.state.settings.anon_runs_per_day),
        resets_at=reset,
    )
