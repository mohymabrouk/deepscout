import pytest
from app.core.errors import PROVIDER_UNAVAILABLE, DomainError
from app.providers.llm.reliable import ReliableLLMProvider
from app.providers.search.reliable import ReliableSearchProvider
from app.research.budget import RunBudget
from app.research.models import LLMRequest, LLMResponse, LLMUsage, SearchResult


class FlakyLLM:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    async def complete(self, request):
        self.calls += 1
        if self.calls <= self.failures:
            raise DomainError(PROVIDER_UNAVAILABLE, "temporary", 503)
        return LLMResponse('{"ok": true}', LLMUsage(10, 5), "fake", "fake")


class FlakySearch:
    def __init__(self) -> None:
        self.calls = 0

    async def search(self, query: str, limit: int) -> list[SearchResult]:
        self.calls += 1
        if self.calls == 1:
            raise DomainError("SEARCH_UNAVAILABLE", "temporary", 503)
        return [SearchResult("https://example.com", "Example", "snippet", "example.com")]


@pytest.mark.anyio
async def test_llm_retry_is_counted_against_run_budget():
    primary = FlakyLLM(failures=1)
    provider = ReliableLLMProvider(primary, None, max_retries=1, backoff_seconds=0)
    request = LLMRequest("planner", [{"role": "user", "content": "question"}], 100, 0.1)
    budget = RunBudget(max_llm_calls=2, max_input_tokens=1000, max_output_tokens=500)
    response = await provider.complete(request, budget)
    assert response.content == '{"ok": true}'
    assert primary.calls == 2
    assert budget.llm_calls == 2


@pytest.mark.anyio
async def test_llm_fallback_uses_a_second_counted_call():
    primary = FlakyLLM(failures=10)
    fallback = FlakyLLM(failures=0)
    provider = ReliableLLMProvider(primary, fallback, max_retries=0, backoff_seconds=0)
    request = LLMRequest("planner", [{"role": "user", "content": "question"}], 100, 0.1)
    budget = RunBudget(max_llm_calls=2, max_input_tokens=1000, max_output_tokens=500)
    response = await provider.complete(request, budget)
    assert response.provider == "fake"
    assert primary.calls == 1 and fallback.calls == 1
    assert budget.llm_calls == 2


@pytest.mark.anyio
async def test_search_retries_transient_failure_once():
    search = FlakySearch()
    provider = ReliableSearchProvider(search, max_retries=1, backoff_seconds=0)
    result = await provider.search("test", 1)
    assert len(result) == 1
    assert search.calls == 2
