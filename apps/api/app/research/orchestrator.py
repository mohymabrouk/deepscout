from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from app.config import Settings
from app.core.errors import INSUFFICIENT_SOURCES, RUN_TIMEOUT, DomainError
from app.db.repository import DocumentRecord, InMemoryRunRepository
from app.providers.llm.factory import create_llm_provider
from app.providers.search.factory import create_search_provider
from app.research.budget import RunBudget
from app.research.evidence import EvidenceSelector
from app.research.fetcher import SafeFetcher
from app.research.models import FetchedPage, SearchResult
from app.research.planner import Planner
from app.research.quality import SourceQualityClassifier
from app.research.synthesizer import Synthesizer
from app.research.verifier import CitationVerifier
from app.schemas.events import RunEvent
from app.schemas.research import Source, Usage

StageCallback = Callable[[str, str, dict], Awaitable[None]]


class ResearchOrchestrator:
    def __init__(self, settings: Settings, repository: InMemoryRunRepository) -> None:
        self.settings, self.repository = settings, repository

    async def run(
        self,
        run_id: str,
        question: str,
        documents: list[DocumentRecord] | None = None,
        on_stage: StageCallback | None = None,
    ) -> None:
        budget = RunBudget(
            self.settings.max_llm_calls_per_run,
            self.settings.max_input_tokens_per_run,
            self.settings.max_output_tokens_per_run,
        )
        active_stage: tuple[str, datetime] | None = None

        async def close_stage(status: str = "completed") -> None:
            nonlocal active_stage
            if active_stage is not None:
                name, started_at = active_stage
                await self.repository.record_stage(run_id, name, started_at, datetime.now(UTC), status)
                active_stage = None

        async def stage(name: str, message: str, data: dict | None = None) -> None:
            nonlocal active_stage
            if active_stage is None:
                active_stage = (name, datetime.now(UTC))
            elif active_stage[0] != name:
                await close_stage()
                active_stage = (name, datetime.now(UTC))
            await self.repository.update_status(run_id, name)
            await self.repository.append_event(
                run_id, RunEvent(event="stage", stage=name, message=message, data=data or {})
            )
            if on_stage:
                await on_stage(name, message, data or {})

        try:
            provider = create_llm_provider(self.settings)
            search_provider = create_search_provider(self.settings)
            await stage("planning", "Planning search")
            plan = await Planner(provider, budget, self.settings.max_search_queries).plan(question)
            await stage("searching", "Searching sources")
            search_results: list[SearchResult] = []
            for query in plan.queries:
                search_results.extend(
                    await search_provider.search(query, self.settings.max_search_results_per_query)
                )
                await self.repository.increment_search_calls(run_id)
            unique_results = list({result.url: result for result in search_results}.values())
            await self.repository.append_event(
                run_id,
                RunEvent(
                    event="stage",
                    stage="searching",
                    message="Searching sources",
                    data={"sources_found": len(unique_results)},
                ),
            )
            await stage(
                "fetching",
                "Reading sources",
                {"total": min(len(unique_results), self.settings.max_fetched_pages)},
            )
            pages = await SafeFetcher(self.settings).fetch_many(
                unique_results, self.settings.max_fetched_pages
            )
            for document in documents or []:
                pages.append(
                    FetchedPage(
                        url=f"local://document/{document.id}",
                        title=document.filename,
                        text=document.extracted_text,
                        domain="uploaded PDF",
                        status_code=200,
                        content_type="application/pdf",
                    )
                )
            await self.repository.set_fetch_counts(run_id, len(unique_results[: self.settings.max_fetched_pages]), len(pages))
            if len(pages) < 1:
                raise DomainError(
                    INSUFFICIENT_SOURCES, "Not enough usable sources were retrieved.", 502
                )
            await stage(
                "fetching",
                "Reading sources",
                {
                    "completed": len(pages),
                    "total": min(len(unique_results), self.settings.max_fetched_pages),
                },
            )
            await stage("selecting", "Selecting evidence")
            evidence = EvidenceSelector(
                self.settings.max_total_context_chars, min(6, self.settings.max_fetched_pages)
            ).select(question, pages, plan.must_cover)
            if not evidence:
                raise DomainError(
                    INSUFFICIENT_SOURCES, "Not enough relevant evidence was retrieved.", 502
                )
            await stage("synthesizing", "Writing report")
            report = await Synthesizer(provider, budget).synthesize(question, evidence)
            await stage("verifying", "Verifying citations")
            report, _ = CitationVerifier().verify(report, evidence)
            await close_stage()
            sources = [
                Source(
                    citation_id=index,
                    title=item.source.title,
                    url=item.source.url,
                    domain=item.source.domain,
                    retrieved_at=item.source.retrieved_at,
                    quality=SourceQualityClassifier().classify(item.source),
                )
                for index, item in enumerate(evidence, start=1)
            ]
            input_tokens, output_tokens, llm_calls = budget.usage()
            await self.repository.complete(
                run_id,
                report,
                sources,
                Usage(input_tokens=input_tokens, output_tokens=output_tokens, llm_calls=llm_calls),
                evidence,
            )
            await self.repository.finalize_metrics(run_id, datetime.now(UTC), budget)
            await self.repository.append_event(
                run_id, RunEvent(event="complete", data={"run_id": run_id, "status": "completed"})
            )
        except TimeoutError:
            await close_stage("failed")
            await self.repository.fail(run_id, "failed", RUN_TIMEOUT)
            await self.repository.append_event(
                run_id, RunEvent(event="error", data={"code": RUN_TIMEOUT})
            )
        except DomainError as exc:
            await close_stage("failed")
            await self.repository.fail(
                run_id, "limited" if exc.code == "TOKEN_BUDGET_EXCEEDED" else "failed", exc.code
            )
            await self.repository.append_event(
                run_id, RunEvent(event="error", data={"code": exc.code, "message": exc.message})
            )
        except Exception:
            await close_stage("failed")
            await self.repository.fail(run_id, "failed", "INTERNAL_ERROR")
            await self.repository.append_event(
                run_id, RunEvent(event="error", data={"code": "INTERNAL_ERROR"})
            )
