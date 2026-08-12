from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    return {"status": "ok", "version": request.app.state.settings.app_version}


@router.get("/ready")
async def ready(request: Request) -> dict[str, bool | str]:
    return {"status": "ready", "database": bool(request.app.state.settings.database_url) or True}
