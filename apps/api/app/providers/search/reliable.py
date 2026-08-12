from __future__ import annotations

import asyncio

from app.core.errors import SEARCH_UNAVAILABLE, DomainError
from app.research.models import SearchProvider, SearchResult


class ReliableSearchProvider:
    def __init__(self, primary: SearchProvider, max_retries: int, backoff_seconds: float) -> None:
        self.primary = primary
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    async def search(self, query: str, limit: int) -> list[SearchResult]:
        for attempt in range(self.max_retries + 1):
            try:
                return await self.primary.search(query, limit)
            except DomainError as exc:
                if exc.code != SEARCH_UNAVAILABLE or attempt >= self.max_retries:
                    raise
                await asyncio.sleep(self.backoff_seconds * (2**attempt))
        raise DomainError(SEARCH_UNAVAILABLE, "The search provider is unavailable.", 503)
