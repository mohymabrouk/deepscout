from __future__ import annotations

import asyncio
import socket
from urllib.parse import urljoin, urlsplit

import httpx

from app.config import Settings
from app.core.errors import DomainError
from app.core.security import is_public_ip, validate_fetch_url
from app.research.extractor import ContentExtractor
from app.research.models import FetchedPage, SearchResult

ALLOWED_CONTENT_TYPES = {"text/html", "text/plain", "application/xhtml+xml"}


class SafeFetcher:
    def __init__(self, settings: Settings, extractor: ContentExtractor | None = None) -> None:
        self.settings = settings
        self.extractor = extractor or ContentExtractor(settings.max_extracted_chars_per_source)

    async def _assert_public_host(self, hostname: str) -> None:
        try:
            infos = await asyncio.get_running_loop().run_in_executor(
                None, socket.getaddrinfo, hostname, None
            )
        except socket.gaierror as exc:
            raise DomainError(
                "SEARCH_UNAVAILABLE", "The source host could not be resolved.", 502
            ) from exc
        addresses = {info[4][0] for info in infos}
        if not addresses or any(not is_public_ip(address) for address in addresses):
            raise DomainError("INVALID_REQUEST", "Private network URLs are not fetchable.", 400)

    async def fetch_one(self, result: SearchResult) -> FetchedPage | None:
        current_url = validate_fetch_url(result.url)
        parsed = urlsplit(current_url)
        # Demo content is local and deterministic; this path never performs network I/O.
        if parsed.hostname == "demo.local":
            title, text = self.extractor.extract(
                f"<html><head><title>{result.title}</title></head><body><main><p>{result.snippet}</p><p>This fixture exists so local development and tests are useful without paid providers.</p></main></body></html>",
                result.title,
            )
            return FetchedPage(current_url, title, text, result.domain)
        await self._assert_public_host(parsed.hostname or "")
        timeout = httpx.Timeout(self.settings.fetch_timeout_seconds)
        headers = {"User-Agent": "DeepScout/0.1 (+https://deepscout.local/research)"}
        try:
            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=False, headers=headers
            ) as client:
                for _ in range(4):
                    response = await client.get(current_url)
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            return None
                        current_url = validate_fetch_url(urljoin(current_url, location))
                        await self._assert_public_host(urlsplit(current_url).hostname or "")
                        continue
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    if response.status_code >= 400 or content_type not in ALLOWED_CONTENT_TYPES:
                        return None
                    body = response.content
                    if len(body) > self.settings.max_fetch_bytes:
                        return None
                    if content_type == "text/plain":
                        title, text = (
                            result.title,
                            body.decode(response.encoding or "utf-8", errors="replace"),
                        )
                    else:
                        title, text = self.extractor.extract(
                            body.decode(response.encoding or "utf-8", errors="replace"),
                            result.title,
                        )
                    if not text:
                        return None
                    return FetchedPage(
                        current_url,
                        title or result.title,
                        text,
                        urlsplit(current_url).hostname or result.domain,
                        status_code=response.status_code,
                        content_type=content_type,
                    )
        except (httpx.TimeoutException, httpx.NetworkError, UnicodeError):
            return None
        return None

    async def fetch_many(self, results: list[SearchResult], max_pages: int) -> list[FetchedPage]:
        unique: list[SearchResult] = []
        seen: set[str] = set()
        for result in results:
            normalized = validate_fetch_url(result.url)
            if normalized not in seen:
                seen.add(normalized)
                unique.append(result)
            if len(unique) >= max_pages:
                break
        semaphore = asyncio.Semaphore(self.settings.fetch_concurrency)

        async def bounded(result: SearchResult) -> FetchedPage | None:
            async with semaphore:
                return await self.fetch_one(result)

        fetched = await asyncio.gather(*(bounded(result) for result in unique))
        return [page for page in fetched if page is not None]
