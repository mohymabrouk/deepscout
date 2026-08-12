from __future__ import annotations

import httpx

from app.core.errors import SEARCH_UNAVAILABLE, DomainError
from app.research.models import SearchResult


class BraveSearchProvider:
    def __init__(self, api_key: str, timeout: float = 10.0) -> None:
        self.api_key = api_key
        self.timeout = timeout

    async def search(self, query: str, limit: int) -> list[SearchResult]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": limit},
                    headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise DomainError(
                SEARCH_UNAVAILABLE, "The search provider is unavailable.", 503
            ) from exc
        if response.status_code >= 400:
            raise DomainError(SEARCH_UNAVAILABLE, "The search provider returned an error.", 503)
        try:
            results = response.json().get("web", {}).get("results", [])
            return [
                SearchResult(
                    url=item["url"],
                    title=item.get("title") or item["url"],
                    snippet=item.get("description", ""),
                    domain=item["url"].split("/")[2],
                )
                for item in results
                if item.get("url")
            ]
        except (ValueError, KeyError, TypeError) as exc:
            raise DomainError(
                SEARCH_UNAVAILABLE, "The search provider returned malformed data.", 503
            ) from exc
