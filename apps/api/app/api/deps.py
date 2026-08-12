from collections.abc import AsyncIterator

from fastapi import Request

from app.config import Settings
from app.core.errors import UNAUTHORIZED, DomainError
from app.core.security import AuthUser
from app.db.repository import InMemoryRunRepository


def get_settings_from_request(request: Request) -> Settings:
    return request.app.state.settings


def get_repository(request: Request) -> InMemoryRunRepository:
    return request.app.state.repository


def get_current_user(request: Request) -> AuthUser:
    user = getattr(request.state, "user", None)
    if user is None:
        raise DomainError(UNAUTHORIZED, "Sign in to access this resource.", 401)
    return user


async def request_id(request: Request) -> AsyncIterator[str]:
    yield request.state.request_id
