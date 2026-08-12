from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from statistics import median
from typing import Any

URL_PATTERN = re.compile(r"https?://[^\s)\]>]+")


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    question: str
    category: str
    must_include_concepts: tuple[str, ...] = ()
    min_sources: int = 1


@dataclass
class CaseMetrics:
    case_id: str
    category: str
    status: str
    completed: bool
    latency_ms: float | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    llm_calls: int
    pages_attempted: int
    pages_succeeded: int
    fetch_success_fraction: float
    unique_cited_sources: int
    unique_cited_domains: int
    source_diversity: float
    invalid_citation_ids: int
    citation_url_integrity: bool
    material_paragraphs: int
    cited_material_paragraphs: int
    citation_coverage: float
    retrieval_sufficiency: bool
    concept_coverage: float
    answer_length_chars: int
    provider_fallback_used: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _report_text(report: Any) -> str:
    if report is None:
        return ""
    sections = _value(report, "sections", []) or []
    paragraphs = [
        str(_value(paragraph, "text", ""))
        for section in sections
        for paragraph in (_value(section, "paragraphs", []) or [])
    ]
    return " ".join(
        [str(_value(report, "title", "")), str(_value(report, "executive_summary", "")), *paragraphs]
    ).strip()


def _paragraphs(report: Any) -> list[Any]:
    return [
        paragraph
        for section in (_value(report, "sections", []) or [])
        for paragraph in (_value(section, "paragraphs", []) or [])
    ]


def evaluate_case(case: EvaluationCase, record: Any) -> CaseMetrics:
    report = _value(record, "report")
    sources = _value(record, "sources", []) or []
    usage = _value(record, "usage")
    metrics = _value(record, "metrics")
    source_by_id = {_value(source, "citation_id"): source for source in sources}
    paragraphs = _paragraphs(report)
    material = [paragraph for paragraph in paragraphs if len(str(_value(paragraph, "text", "")).strip()) >= 25]
    cited_ids = {
        citation
        for paragraph in paragraphs
        for citation in (_value(paragraph, "citations", []) or [])
    }
    invalid_ids = cited_ids - set(source_by_id)
    valid_cited_ids = cited_ids & set(source_by_id)
    cited_domains = {
        _value(source_by_id[citation], "domain", "")
        for citation in valid_cited_ids
    }
    cited_material = [
        paragraph
        for paragraph in material
        if any(citation in source_by_id for citation in (_value(paragraph, "citations", []) or []))
    ]
    report_urls = set(URL_PATTERN.findall(_report_text(report)))
    source_urls = {_value(source, "url", "") for source in sources}
    url_integrity = report_urls.issubset(source_urls) and all(
        url.startswith(("http://", "https://")) for url in source_urls
    )
    concepts = [concept.lower().strip() for concept in case.must_include_concepts if concept.strip()]
    report_text = _report_text(report).lower()
    concept_coverage = sum(concept in report_text for concept in concepts) / len(concepts) if concepts else 1.0
    pages_attempted = int(_value(metrics, "pages_attempted", 0) or 0)
    pages_succeeded = int(_value(metrics, "pages_succeeded", 0) or 0)
    input_tokens = int(_value(usage, "input_tokens", 0) or 0)
    output_tokens = int(_value(usage, "output_tokens", 0) or 0)
    return CaseMetrics(
        case_id=case.id,
        category=case.category,
        status=str(_value(record, "status", "unknown")),
        completed=str(_value(record, "status", "")) == "completed",
        latency_ms=_value(metrics, "latency_ms"),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        llm_calls=int(_value(usage, "llm_calls", 0) or 0),
        pages_attempted=pages_attempted,
        pages_succeeded=pages_succeeded,
        fetch_success_fraction=pages_succeeded / pages_attempted if pages_attempted else 0.0,
        unique_cited_sources=len(valid_cited_ids),
        unique_cited_domains=len(cited_domains),
        source_diversity=len(cited_domains) / len(valid_cited_ids) if valid_cited_ids else 0.0,
        invalid_citation_ids=len(invalid_ids),
        citation_url_integrity=url_integrity,
        material_paragraphs=len(material),
        cited_material_paragraphs=len(cited_material),
        citation_coverage=len(cited_material) / len(material) if material else 0.0,
        retrieval_sufficiency=len(sources) >= case.min_sources,
        concept_coverage=concept_coverage,
        answer_length_chars=len(_report_text(report)),
        provider_fallback_used=bool(_value(metrics, "fallback_used", False)),
    )


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def aggregate_metrics(cases: list[CaseMetrics], include_categories: bool = True) -> dict[str, Any]:
    count = len(cases)
    completed = sum(case.completed for case in cases)
    invalid = sum(case.invalid_citation_ids > 0 for case in cases)
    latencies = [case.latency_ms for case in cases if case.latency_ms is not None]
    tokens = [case.total_tokens for case in cases]
    return {
        "case_count": count,
        "completed_count": completed,
        "completion_rate": completed / count if count else 0.0,
        "invalid_citation_case_rate": invalid / count if count else 0.0,
        "citation_coverage": sum(case.citation_coverage for case in cases) / count if count else 0.0,
        "citation_url_integrity_rate": sum(case.citation_url_integrity for case in cases) / count if count else 0.0,
        "retrieval_sufficiency_rate": sum(case.retrieval_sufficiency for case in cases) / count if count else 0.0,
        "concept_coverage": sum(case.concept_coverage for case in cases) / count if count else 0.0,
        "median_latency_ms": median(latencies) if latencies else None,
        "p95_latency_ms": _percentile(latencies, 0.95),
        "median_total_tokens": median(tokens) if tokens else 0,
        "median_llm_calls": median([case.llm_calls for case in cases]) if cases else 0,
        "median_sources": median([case.unique_cited_sources for case in cases]) if cases else 0,
        "provider_fallback_rate": sum(case.provider_fallback_used for case in cases) / count if count else 0.0,
        "categories": {
            category: aggregate_metrics(
                [case for case in cases if case.category == category], include_categories=False
            )
            for category in sorted({case.category for case in cases})
        } if include_categories else {},
    }


def regression_gate(current: dict[str, Any], baseline: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if current.get("invalid_citation_case_rate", 0) > baseline.get("invalid_citation_case_rate", 0):
        failures.append("invalid citation rate increased")
    if current.get("completion_rate", 0) < baseline.get("completion_rate", 0) - 0.05:
        failures.append("completion rate regressed by more than 5 percentage points")
    baseline_tokens = baseline.get("median_total_tokens", 0)
    if baseline_tokens and current.get("median_total_tokens", 0) > baseline_tokens * 1.2:
        failures.append("median token usage increased by more than 20%")
    return not failures, failures
