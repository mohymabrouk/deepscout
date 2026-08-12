from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1] / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.config import Settings  # noqa: E402
from app.db.repository import InMemoryRunRepository  # noqa: E402
from app.research.orchestrator import ResearchOrchestrator  # noqa: E402
from metrics import EvaluationCase, aggregate_metrics, evaluate_case, regression_gate  # noqa: E402


def load_cases(path: Path) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            case = EvaluationCase(
                id=str(payload["id"]),
                question=str(payload["question"]),
                category=str(payload["category"]),
                must_include_concepts=tuple(str(item) for item in payload.get("must_include_concepts", [])),
                min_sources=int(payload.get("min_sources", 1)),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid eval case on line {line_number}: {exc}") from exc
        if len(case.question) < 10 or case.min_sources < 1:
            raise ValueError(f"Invalid eval case constraints for {case.id}")
        cases.append(case)
    if not cases:
        raise ValueError("Evaluation dataset is empty")
    return cases


async def run_cases(cases: list[EvaluationCase]) -> list:
    settings = Settings(
        llm_provider="demo",
        search_provider="demo",
        anon_runs_per_day=max(100, len(cases)),
        auth_runs_per_day=max(100, len(cases)),
    )
    results = []
    for case in cases:
        repository = InMemoryRunRepository()
        run = await repository.create(case.question, f"eval:{case.id}")
        started = time.perf_counter()
        await ResearchOrchestrator(settings, repository).run(run.id, run.question)
        elapsed_ms = (time.perf_counter() - started) * 1000
        record = await repository.get(run.id)
        if record is None:
            raise RuntimeError(f"Run disappeared for eval case {case.id}")
        if record.metrics.latency_ms is None:
            record.metrics.completed_at = datetime.now(UTC)
        metric = evaluate_case(case, record)
        metric.latency_ms = metric.latency_ms or elapsed_ms
        results.append(metric)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic DeepScout evaluation cases")
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("cases.jsonl"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--fail-on-regression", action="store_true")
    args = parser.parse_args()
    cases = load_cases(args.cases)
    metrics = asyncio.run(run_cases(cases))
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "cases": [metric.as_dict() for metric in metrics],
        "aggregate": aggregate_metrics(metrics),
    }
    if args.baseline:
        baseline = json.loads(args.baseline.read_text())
        passed, failures = regression_gate(payload["aggregate"], baseline["aggregate"])
        payload["regression"] = {"passed": passed, "failures": failures}
        if args.fail_on_regression and not passed:
            print(json.dumps(payload, indent=2))
            return 1
    rendered = json.dumps(payload, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

