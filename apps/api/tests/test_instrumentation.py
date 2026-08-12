import asyncio

from app.config import Settings
from app.db.repository import InMemoryRunRepository
from app.research.orchestrator import ResearchOrchestrator


def test_demo_run_records_stage_and_latency_metrics():
    async def run():
        repository = InMemoryRunRepository()
        record = await repository.create("Explain bounded web retrieval for a research tool.", "eval")
        await ResearchOrchestrator(Settings(), repository).run(record.id, record.question)
        return await repository.get(record.id)

    record = asyncio.run(run())
    assert record is not None
    assert record.status == "completed"
    assert record.metrics.latency_ms is not None
    assert record.metrics.pages_attempted >= record.metrics.pages_succeeded >= 1
    assert record.metrics.search_calls == 3
    assert {item.stage for item in record.metrics.stage_timings} == {
        "planning", "searching", "fetching", "selecting", "synthesizing", "verifying"
    }
    assert all(item.duration_ms is not None for item in record.metrics.stage_timings)
    assert "retrieved evidence says" in record.report.sections[0].paragraphs[0].text.lower()
