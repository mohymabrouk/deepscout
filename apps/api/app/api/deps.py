from collections.abc import AsyncIterator

from fastapi import Request

from app.config import Settings
from app.db.repository import InMemoryRunRepository


def get_settings_from_request(request: Request) -> Settings:
    return request.app.state.settings


def get_repository(request: Request) -> InMemoryRunRepository:
    return request.app.state.repository


async def request_id(request: Request) -> AsyncIterator[str]:
    yield request.state.request_id
