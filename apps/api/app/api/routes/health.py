from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    return {"status": "ok", "version": request.app.state.settings.app_version}


@router.get("/ready")
async def ready(request: Request) -> dict[str, bool | str]:
    try:
        database_ready = await request.app.state.repository.ready()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready.") from exc
    return {"status": "ready", "database": database_ready}
