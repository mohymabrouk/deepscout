from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.research import router as research_router
from app.api.routes.usage import router as usage_router
from app.config import get_settings
from app.core.errors import HTTP_RATE_LIMIT, DomainError
from app.core.rate_limit import FixedWindowRateLimiter, RunQuotaService
from app.core.security import request_identity
from app.db.repository import InMemoryRunRepository
from app.research.orchestrator import ResearchOrchestrator


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="DeepScout API", version=settings.app_version)
    app.state.settings = settings
    app.state.repository = InMemoryRunRepository()
    app.state.orchestrator = ResearchOrchestrator(settings, app.state.repository)
    app.state.tasks = set()
    app.state.rate_limiter = FixedWindowRateLimiter()
    app.state.quota_service = RunQuotaService()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex}")
        if request.url.path.startswith("/v1"):
            raw_ip = request.client.host if request.client else "unknown"
            identity, authenticated = request_identity(
                request.headers.get("Authorization"), raw_ip, settings.anon_id_hmac_secret
            )
            request.state.identity_key = identity
            request.state.authenticated = authenticated
            limit = settings.http_requests_per_minute_auth if authenticated else settings.http_requests_per_minute_anon
            allowed, remaining, reset = await app.state.rate_limiter.check(identity, limit)
            if not allowed:
                response = JSONResponse(
                    status_code=429,
                    content={"error": {"code": HTTP_RATE_LIMIT, "message": "Too many API requests. Please retry shortly.", "request_id": request.state.request_id, "retry_after_seconds": reset}},
                )
                response.headers["Retry-After"] = str(reset)
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(reset)
                return response
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/v1"):
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset)
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        payload = {
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request.state.request_id,
                "retry_after_seconds": exc.retry_after_seconds,
                "details": exc.details,
            }
        }
        response = JSONResponse(status_code=exc.status_code, content=payload)
        if exc.retry_after_seconds is not None:
            response.headers["Retry-After"] = str(exc.retry_after_seconds)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        response = JSONResponse(
            status_code=422,
            content={"error": {"code": "INVALID_REQUEST", "message": "Request validation failed.", "request_id": request.state.request_id, "details": {"fields": jsonable_encoder(exc.errors())}}},
        )
        return response

    app.include_router(health_router)
    app.include_router(research_router)
    app.include_router(usage_router)
    return app


app = create_app()
