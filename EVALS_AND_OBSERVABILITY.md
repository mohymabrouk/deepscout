# Evals & Observability

## 1. Why evals are mandatory

DeepScout is a portfolio project for AI engineering. The evaluation layer proves you can measure reliability rather than judge outputs only by intuition.

## 2. Eval dataset

Start with 30-50 curated questions, then grow toward 100+.

Categories:

```text
technical comparison
technical explanation
market landscape
fact verification
recency-sensitive research
ambiguous question
insufficient evidence
provider/search failure simulation
```

JSONL example:

```json
{"id":"tech_001","question":"Compare pgvector with a hosted vector DB for a small SaaS.","must_include_concepts":["operational burden","cost","scaling"],"min_sources":3}
```

## 3. Deterministic metrics

Per run:

- completed / failed;
- latency;
- LLM call count;
- input/output tokens;
- pages fetched;
- fetch success ratio;
- number of unique cited sources;
- invalid citation IDs;
- citation URL integrity;
- answer length;
- provider fallback used.

## 4. Heuristic quality metrics

Examples:

### Citation coverage

```text
material paragraphs with >=1 citation
--------------------------------------
material factual paragraphs
```

### Source diversity

Unique cited domains / total cited sources.

### Retrieval sufficiency

Pass if usable source count >= case-specific minimum.

## 5. LLM-as-judge

Optional after deterministic checks.

Judge dimensions:

- relevance;
- completeness;
- evidence faithfulness;
- clarity;
- calibrated uncertainty.

Do not let one judge score become the entire benchmark. Store judge model/version.

## 6. Regression gate

CI can run a small smoke eval set on mocked providers for every PR.

A scheduled/manual full eval can run against live free APIs when desired.

Suggested gate:

```text
no increase in invalid citation rate
completion rate does not regress > 5 percentage points
median token usage does not increase > 20% without justification
```

## 7. Tracing

Each run should have stage spans:

```text
research.run
  planning
  search
  fetch
  extract
  evidence_select
  synthesize
  verify
  persist
```

Each span records start/end, status, latency, and selected counters.

## 8. Dashboard

A simple internal page or SQL notebook is enough for MVP.

Track:

```text
runs/day
completion rate
p50/p95 latency
provider 429 count
input/output tokens per run
sources per run
fetch failure rate
citation repair rate
```

No need for a full observability vendor on day one.
