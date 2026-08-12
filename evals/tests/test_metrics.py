from types import SimpleNamespace

from evals.metrics import EvaluationCase, aggregate_metrics, evaluate_case, regression_gate


def make_record(citations: list[int], source_ids: list[int] | None = None, status: str = "completed"):
    source_ids = source_ids or [1]
    sources = [SimpleNamespace(citation_id=source_id, url=f"https://source-{source_id}.example", domain=f"source-{source_id}.example") for source_id in source_ids]
    report = SimpleNamespace(
        title="Brief",
        executive_summary="Summary",
        sections=[SimpleNamespace(heading="Findings", paragraphs=[SimpleNamespace(text="A material factual finding.", citations=citations)])],
    )
    return SimpleNamespace(
        status=status,
        report=report,
        sources=sources,
        usage=SimpleNamespace(input_tokens=10, output_tokens=5, llm_calls=2),
        metrics=SimpleNamespace(latency_ms=20.0, pages_attempted=2, pages_succeeded=2, fallback_used=False),
    )


def test_metrics_detect_invalid_citations_and_measure_coverage():
    metric = evaluate_case(EvaluationCase("x", "A valid question here", "technical explanation"), make_record([1, 99]))
    assert metric.invalid_citation_ids == 1
    assert metric.citation_coverage == 1.0
    assert metric.citation_url_integrity


def test_aggregate_metrics_and_regression_gate():
    cases = [evaluate_case(EvaluationCase("x", "A valid question here", "technical explanation"), make_record([1]))]
    aggregate = aggregate_metrics(cases)
    assert aggregate["completion_rate"] == 1.0
    passed, failures = regression_gate(aggregate, aggregate)
    assert passed and not failures
    failed, failures = regression_gate({**aggregate, "median_total_tokens": 100}, aggregate)
    assert not failed
    assert "median token usage increased by more than 20%" in failures
