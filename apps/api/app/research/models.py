from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str
    snippet: str
    domain: str
    published_at: datetime | None = None


@dataclass
class FetchedPage:
    url: str
    title: str
    text: str
    domain: str
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status_code: int = 200
    content_type: str = "text/html"


@dataclass(frozen=True)
class EvidencePassage:
    source_index: int
    source: FetchedPage
    excerpt: str
    relevance_score: float


@dataclass(frozen=True)
class PlannerResult:
    queries: list[str]
    intent: str
    must_cover: list[str]


@dataclass(frozen=True)
class LLMRequest:
    purpose: Literal["planner", "synthesis", "repair"]
    messages: list[dict[str, str]]
    max_output_tokens: int
    temperature: float


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class LLMResponse:
    content: str
    usage: LLMUsage
    provider: str
    model: str


class LLMProvider(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResponse: ...


class SearchProvider(Protocol):
    async def search(self, query: str, limit: int) -> list[SearchResult]: ...


class PageFetcher(Protocol):
    async def fetch_many(
        self, results: list[SearchResult], max_pages: int
    ) -> list[FetchedPage]: ...


def report_payload(report: Any) -> dict[str, Any]:
    """Serialize either a Pydantic report or a test double without leaking internals."""
    if hasattr(report, "model_dump"):
        return report.model_dump(mode="json")
    return dict(report)
