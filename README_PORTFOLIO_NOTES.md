# Portfolio Positioning Notes

These notes are for the final public GitHub README and interview preparation.

## What to emphasize

Do not describe the project merely as "an AI research agent."

Emphasize engineering decisions:

- bounded orchestration instead of an uncontrolled agent loop;
- provider abstraction and fallback;
- request and token quotas for free-tier protection;
- safe retrieval with SSRF defenses;
- structured outputs;
- citation integrity;
- measurable eval suite;
- latency/token observability;
- deployment constraints and trade-offs.

## Good README benchmark section

Example format:

```text
Evaluation set: 50 research questions
Completion rate: 94%
Valid citation references: 100%
Median sources cited: 4
Median latency: 14.2s
Median LLM calls/run: 2
Median input tokens/run: 7.8k
```

Use only numbers you actually measured.

## Interview story

A strong explanation follows:

1. problem;
2. constraints (free tier, latency, source trust);
3. architecture;
4. biggest failure mode found;
5. metric used to detect it;
6. change made;
7. measured improvement;
8. next scaling step.

## Resume bullet template

Replace placeholders with measured values:

```text
Built and deployed DeepScout, a source-backed AI research system using Next.js, FastAPI, Postgres, and LLM/search APIs; implemented bounded orchestration, citation verification, SSRF-safe retrieval, per-user/token rate limits, and an automated eval suite across N test cases, achieving X% completion and Y% citation validity.
```
