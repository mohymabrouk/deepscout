import pytest
from app.core.errors import DomainError
from app.core.rate_limit import FixedWindowRateLimiter, RunQuotaService
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.mark.anyio
async def test_daily_quota_and_concurrency_reservations_are_atomic():
    quota = RunQuotaService()
    await quota.reserve_run("identity", daily_limit=1, concurrency_limit=1)
    with pytest.raises(DomainError) as daily_error:
        await quota.reserve_run("identity", daily_limit=1, concurrency_limit=1)
    assert daily_error.value.code == "DAILY_RUN_LIMIT"
    await quota.finish_run("identity", input_tokens=12, output_tokens=4, llm_calls=2)
    usage = await quota.get("identity")
    assert usage.active_runs == 0
    assert usage.input_tokens == 12


@pytest.mark.anyio
async def test_rate_limiter_allows_boundary_then_rejects():
    limiter = FixedWindowRateLimiter()
    assert (await limiter.check("identity", limit=2, now=60.0))[0]
    assert (await limiter.check("identity", limit=2, now=60.0))[0]
    allowed, remaining, retry_after = await limiter.check("identity", limit=2, now=60.0)
    assert not allowed
    assert remaining == 0
    assert retry_after == 60


def test_usage_endpoint_and_rate_headers_are_structured():
    app = create_app()
    app.state.settings.enable_debug_usage = True
    with TestClient(app) as client:
        response = client.get("/v1/usage")
        assert response.status_code == 200
        assert response.json()["runs_used"] == 0
        assert response.headers["X-RateLimit-Limit"]
        assert response.headers["X-Request-ID"].startswith("req_")
