from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.research import router as research_router
from app.api.routes.usage import router as usage_router
from app.config import get_settings
from app.core.errors import DomainError
from app.db.repository import InMemoryRunRepository
from app.research.orchestrator import ResearchOrchestrator


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="DeepScout API", version=settings.app_version)
    app.state.settings = settings
    app.state.repository = InMemoryRunRepository()
    app.state.orchestrator = ResearchOrchestrator(settings, app.state.repository)
    app.state.tasks = set()
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
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
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

    app.include_router(health_router)
    app.include_router(research_router)
    app.include_router(usage_router)
    return app


app = create_app()
