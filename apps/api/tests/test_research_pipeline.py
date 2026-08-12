import asyncio

from app.main import create_app
from app.research.evidence import EvidenceSelector
from app.research.models import FetchedPage
from app.research.verifier import CitationVerifier
from app.schemas.research import ReportParagraph, ReportSection, ResearchReport
from fastapi.testclient import TestClient


def test_demo_orchestrator_completes_with_sources_and_events():
    app = create_app()
    with TestClient(app) as client:
        accepted = client.post(
            "/v1/research",
            json={"question": "Compare pgvector and hosted vector databases for a small SaaS."},
            headers={"Idempotency-Key": "pipeline-test"},
        )
        assert accepted.status_code == 202
        run_id = accepted.json()["run_id"]

        for _ in range(50):
            result = client.get(f"/v1/research/{run_id}").json()
            if result["status"] in {"completed", "failed", "limited"}:
                break
            asyncio.run(asyncio.sleep(0.01))

        assert result["status"] == "completed"
        assert len(result["sources"]) >= 1
        assert all(source["quality"]["label"] in {"high", "medium", "low"} for source in result["sources"])
        assert result["report"]["sections"][0]["paragraphs"][0]["citations"]
        assert result["usage"]["llm_calls"] == 2

        events = client.get(f"/v1/research/{run_id}/events")
        assert events.status_code == 200
        assert "event: complete" in events.text
        for stage in ["planning", "searching", "fetching", "selecting", "synthesizing", "verifying"]:
            assert f'"stage": "{stage}"' in events.text
        assert '"sources_found": 4' in events.text


def test_idempotency_returns_original_run():
    app = create_app()
    with TestClient(app) as client:
        payload = {"question": "Explain bounded web retrieval for an AI research tool."}
        first = client.post("/v1/research", json=payload, headers={"Idempotency-Key": "same"})
        second = client.post("/v1/research", json=payload, headers={"Idempotency-Key": "same"})
        assert first.json()["run_id"] == second.json()["run_id"]


def test_evidence_selector_limits_context_and_diversifies_domains():
    pages = [
        FetchedPage("https://a.example/1", "A", "pgvector scaling and operational burden are important tradeoffs." * 10, "a.example"),
        FetchedPage("https://b.example/1", "B", "Hosted databases reduce operational burden but can cost more." * 10, "b.example"),
        FetchedPage("https://c.example/1", "C", "A third source covers limitations and migration concerns." * 10, "c.example"),
    ]
    evidence = EvidenceSelector(max_context_chars=500, max_sources=3).select("Compare scaling and cost", pages)
    assert len(evidence) == 3
    assert len("".join(item.excerpt for item in evidence)) <= 500


def test_citation_verifier_removes_unknown_ids_and_marks_coverage():
    report = ResearchReport(
        title="Test",
        executive_summary="Summary",
        sections=[ReportSection(heading="Findings", paragraphs=[ReportParagraph(text="Fact", citations=[1, 99])])],
    )
    evidence = [FetchedPage("https://a.example", "A", "Evidence", "a.example")]
    passages = EvidenceSelector().select("Evidence", evidence)
    verified, limitations = CitationVerifier().verify(report, passages)
    assert verified.sections[0].paragraphs[0].citations == [1]
    assert any("removed" in limitation for limitation in limitations)


def test_question_validation_is_structured():
    app = create_app()
    with TestClient(app) as client:
        response = client.post("/v1/research", json={"question": "short"})
        assert response.status_code == 422
