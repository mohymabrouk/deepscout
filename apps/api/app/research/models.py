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
    used_fallback: bool = False


@dataclass
class StageTiming:
    stage: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: float | None = None
    status: Literal["completed", "failed"] = "completed"


@dataclass
class RunMetrics:
    started_at: datetime
    completed_at: datetime | None = None
    stage_timings: list[StageTiming] = field(default_factory=list)
    search_calls: int = 0
    pages_attempted: int = 0
    pages_succeeded: int = 0
    provider_names: list[str] = field(default_factory=list)
    fallback_used: bool = False

    @property
    def latency_ms(self) -> float | None:
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds() * 1000


class LLMProvider(Protocol):
    async def complete(self, request: LLMRequest, budget: Any = None) -> LLMResponse: ...


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
