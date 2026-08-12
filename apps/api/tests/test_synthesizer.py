import pytest
from app.core.errors import INSUFFICIENT_SOURCES, SYNTHESIS_INVALID, DomainError
from app.research.budget import RunBudget
from app.research.models import EvidencePassage, FetchedPage, LLMResponse, LLMUsage
from app.research.synthesizer import Synthesizer


class StubLLM:
    def __init__(self, content: str) -> None:
        self.content = content
        self.request = None

    async def complete(self, request, budget=None):
        self.request = request
        return LLMResponse(self.content, LLMUsage(10, 20), "stub", "stub")


def evidence() -> list[EvidencePassage]:
    page = FetchedPage(
        "https://example.com/energy",
        "Clean energy",
        "Clean energy can reduce emissions and improve air quality.",
        "example.com",
    )
    return [EvidencePassage(1, page, page.text, 1.0)]


def budget() -> RunBudget:
    return RunBudget(max_llm_calls=3, max_input_tokens=2_000, max_output_tokens=2_000)


@pytest.mark.anyio
async def test_synthesizer_accepts_the_report_contract():
    provider = StubLLM(
        '{"title":"Energy benefits","executive_summary":"Cities benefit from clean energy.",'
        '"sections":[{"heading":"Findings","paragraphs":[{"text":"It reduces emissions.","citations":[1]}]}],'
        '"limitations":[]}'
    )

    report = await Synthesizer(provider, budget()).synthesize("Why use clean energy?", evidence())

    assert report.title == "Energy benefits"
    assert report.sections[0].paragraphs[0].citations == [1]
    assert '"sections"' in provider.request.messages[0]["content"] or '"sections"' in provider.request.messages[1]["content"]


@pytest.mark.anyio
async def test_synthesizer_normalizes_groq_benefits_shape():
    provider = StubLLM(
        '{"benefits":[{"description":"Reduce emissions","source_id":"1"},'
        '{"benefit":"Improve air quality","source":["1"]}]}'
    )

    report = await Synthesizer(provider, budget()).synthesize("Why use clean energy?", evidence())

    paragraphs = report.sections[0].paragraphs
    assert [paragraph.text for paragraph in paragraphs] == [
        "Reduce emissions",
        "Improve air quality",
    ]
    assert all(paragraph.citations == [1] for paragraph in paragraphs)


@pytest.mark.anyio
async def test_synthesizer_reports_invalid_provider_output_separately():
    provider = StubLLM('{"benefits":[]}' )

    with pytest.raises(DomainError) as error:
        await Synthesizer(provider, budget()).synthesize("Why use clean energy?", evidence())

    assert error.value.code == SYNTHESIS_INVALID


@pytest.mark.anyio
async def test_synthesizer_keeps_no_evidence_as_insufficient_sources():
    provider = StubLLM("{}")

    with pytest.raises(DomainError) as error:
        await Synthesizer(provider, budget()).synthesize("Why use clean energy?", [])

    assert error.value.code == INSUFFICIENT_SOURCES
