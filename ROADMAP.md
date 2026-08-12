# Implementation Roadmap

## Current implementation status

Phases 1 through 6 are implemented in the local MVP:

- `apps/api`: bounded planner → search → safe fetch → extraction → evidence → synthesis → citation verification pipeline;
- `apps/web`: research composer, stage progress, result report, inline citations, and source cards;
- Phase 2 controls: HMAC identity keys, burst limits, daily run quotas, concurrency reservations, token budgets, bounded fetches, transient retries, optional LLM fallback, and structured errors;
- deterministic demo providers allow the full flow and tests to run without paid API keys;
- `infra/sql/001_initial.sql` and the Phase 5 migration are prepared for managed Postgres deployment.
- Phase 3 UX: live stage telemetry, loading skeletons, responsive report/source layout, citation highlighting/tooltips, keyboard shortcuts, reduced-motion support, automatic dark mode, and share-link copying;
- Phase 4 evals: 32 curated cases, deterministic citation/retrieval/latency/token metrics, checked-in baseline, CI regression gate, and a measured evidence-coverage improvement.
- Phase 6 source-quality classifier: deterministic bounded scores, explainable reasons, Postgres persistence, and source-rail UI signals with an explicit heuristic disclaimer.

The default local repository remains single-process in-memory so the MVP runs without infrastructure. When `DATABASE_URL` is configured, the API uses the Postgres repository; Supabase Auth and owner-scoped history are implemented, while deployment configuration remains environment-specific.

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

Status: implemented with verified Supabase JWTs, owner-scoped result/event access,
Postgres-backed history, signed cursors, and owner-only deletion.

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

Status: source-quality classifier implemented. The classifier is deliberately heuristic
and explainable; it signals observable source characteristics without claiming factual
authority.
