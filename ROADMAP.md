# Implementation Roadmap

## Current implementation status

Phase 1 and Phase 2 are implemented in the local MVP:

- `apps/api`: bounded planner → search → safe fetch → extraction → evidence → synthesis → citation verification pipeline;
- `apps/web`: research composer, stage progress, result report, inline citations, and source cards;
- Phase 2 controls: HMAC identity keys, burst limits, daily run quotas, concurrency reservations, token budgets, bounded fetches, transient retries, optional LLM fallback, and structured errors;
- deterministic demo providers allow the full flow and tests to run without paid API keys;
- `infra/sql/001_initial.sql` is prepared for managed Postgres deployment.

The default local repository is intentionally single-process in-memory so the MVP runs without infrastructure. Postgres repository wiring, auth/history, deployment, and evals remain future hardening work before claiming the production exit criteria.

## Phase 0 — repository foundation

Deliverables:

- monorepo folders;
- Next.js app;
- FastAPI app;
- CI lint/typecheck/test;
- environment validation;
- `/health` endpoint.

Exit criterion: both apps deploy independently.

## Phase 1 — working research MVP

Deliverables:

- question input;
- planner call;
- search adapter;
- safe page fetcher;
- extraction;
- synthesis call;
- result page;
- source cards.

Exit criterion: 10 curated questions produce useful reports.

## Phase 2 — cost and reliability

Deliverables:

- per-IP/user limits;
- run budget object;
- token estimation;
- bounded fetch count;
- provider retry policy;
- optional fallback;
- structured errors.

Exit criterion: repeated abuse cannot consume unlimited free API quota.

## Phase 3 — UX polish

Deliverables:

- stage streaming;
- skeleton/loading states;
- responsive result layout;
- citation interactions;
- keyboard shortcuts;
- dark mode if desired;
- shareable run URL.

Exit criterion: portfolio reviewer understands the product in under 30 seconds.

## Phase 4 — evals

Deliverables:

- 30-50-case eval set;
- deterministic citation metrics;
- latency/token metrics;
- regression script;
- README benchmark table.

Exit criterion: you can quantify at least one improvement between versions.

## Phase 5 — auth/history

Deliverables:

- Supabase Auth;
- history page;
- ownership checks;
- delete run.

Exit criterion: signed-in user can safely revisit their runs.

## Phase 6 — portfolio-grade extras

Choose only one or two:

- PDF ingestion;
- pgvector RAG over user uploads;
- domain-specific mode;
- source-quality classifier;
- comparison tables;
- model/provider A/B eval dashboard;
- cost/latency optimization report.

Do not add multi-agent orchestration unless it produces a measurable gain.
