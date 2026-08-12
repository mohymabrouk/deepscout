# DeepScout

Minimalist, source-backed AI research agent built as a production-minded portfolio MVP.

## Product promise

A user asks a research question. DeepScout turns it into focused search queries, gathers a small set of relevant sources, extracts evidence, synthesizes a concise report, verifies citation coverage, and returns a source-backed answer.

The MVP is intentionally narrow: reliable research runs, clean UX, strict cost controls, and observable behavior matter more than a large feature list.

## Core user flow

1. User enters a research question.
2. Backend validates the request and checks quotas.
3. Planner generates 2-4 search queries.
4. Search layer returns candidate sources.
5. Fetcher downloads a bounded number of pages.
6. Extractor removes boilerplate and keeps useful text.
7. Evidence ranker selects the strongest passages.
8. Synthesizer writes a structured report.
9. Citation verifier checks that material claims are supported.
10. Result is stored and streamed back to the UI.

## MVP scope

### Included

- Single-question research runs
- Anonymous demo mode plus optional auth
- Search + page retrieval
- LLM-based query planning and synthesis
- Source cards and inline citation references
- Streaming progress events
- Per-IP and per-user request limits
- Token budgets per run and per day
- Provider fallback support
- Run history for authenticated users
- Basic eval suite
- Structured logs and traces
- Zero/near-zero-cost deployment profile

### Explicitly excluded from v1

- Browser automation
- Autonomous purchasing/actions
- Long-running background jobs
- Multi-agent swarms
- Arbitrary file upload RAG
- Team workspaces
- Billing
- Self-hosted model serving
- Kubernetes / microservices

## Suggested stack

| Layer | Choice |
|---|---|
| Frontend | Next.js + TypeScript + Tailwind CSS |
| Hosting | Vercel |
| Backend | FastAPI + Python |
| Backend hosting | Render free service or equivalent free container host |
| Database | Supabase Postgres |
| Auth | Supabase Auth |
| Vector search | Not required for v1; pgvector later |
| Inference | Groq-compatible provider adapter; optional OpenRouter fallback |
| Search | Free-tier search provider adapter |
| Observability | Structured logs + DB traces; Langfuse optional later |

## Repository layout

```text
deepscout/
├── apps/
│   ├── web/                 # Next.js frontend
│   └── api/                 # FastAPI backend
├── packages/
│   └── shared/              # Shared schemas/types if desired
├── docs/
├── evals/
│   ├── cases.jsonl
│   └── run_eval.py
├── infra/
│   ├── render.yaml
│   └── sql/
├── .github/workflows/
├── .env.example
├── README.md
└── LICENSE
```

## Product quality bar

A run is considered successful when:

- it completes within the configured latency target;
- it stays under the run token budget;
- at least 3 usable sources are gathered for broad research questions;
- the final answer contains no fabricated URLs;
- material factual claims have supporting citations;
- a provider failure produces a controlled fallback or user-safe error;
- quota exhaustion returns an explicit, non-ambiguous response.

## Local development

The default local configuration uses deterministic `demo` search and LLM adapters, so the complete research flow works without provider credentials. Set `LLM_PROVIDER` and `SEARCH_PROVIDER` in `.env` to use real providers.

Frontend:

```bash
cd apps/web
npm install
npm run dev
```

Backend:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run the validation suite from the repository root:

```bash
.venv/bin/ruff check apps/api
.venv/bin/pytest -q
cd apps/web && npm run lint && npm run typecheck && npm run build && npm audit
```

The API currently uses an in-memory repository for local/demo execution. The initial Postgres schema is in `infra/sql/001_initial.sql`; persistent repository wiring is intentionally separate from the Phase 1–2 local MVP.

## Deterministic benchmark

The Phase 4 smoke evaluation contains 32 cases across technical comparisons, explanations, landscapes, fact checks, recency-sensitive questions, ambiguity, insufficient evidence, provider failures, and retrieval security. It runs against deterministic demo providers and is regression-gated in CI.

| Metric | Demo baseline / current |
|---|---:|
| Completion rate | 100% |
| Invalid citation case rate | 0% |
| Citation coverage | 100% |
| Citation URL integrity | 100% |
| Retrieval sufficiency | 100% |
| Concept coverage (demo-v1 → demo-v2) | 5.2% → 14.6% (+9.375 pp) |
| Median total tokens | 650.0 |
| Median model calls | 2 |

Run details and the regression policy are in [`evals/README.md`](evals/README.md).

Copy `.env.example` into the relevant app environment files and fill only the services you are using.

## Recommended build order

1. Health endpoint and static UI shell
2. `/v1/research` non-streaming happy path
3. Search adapter + fetcher
4. LLM planner + synthesis
5. Source storage + report rendering
6. Streaming progress
7. Rate limiting + token budgets
8. Citation verification
9. Auth + history
10. Evals, monitoring, deployment hardening

See the rest of this documentation pack for the implementation contracts.
