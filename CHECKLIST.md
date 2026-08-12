# Build Checklist

## Phase 1–4 implementation note

The checked implementation items below run locally against deterministic demo providers. Items involving managed persistence, authentication, deployment, or live evals are not marked complete until their external integrations are wired and validated.

## Repository

- [x] Create `apps/web`
- [x] Create `apps/api`
- [x] Add root README
- [x] Add `.env.example`
- [x] Add CI
- [ ] Protect `main` branch if desired

## Backend

- [x] Config validation
- [x] Health endpoint
- [x] Error schema
- [x] Request ID middleware
- [x] CORS
- [x] Rate limiter
- [x] Run budget manager
- [x] LLM provider interface
- [x] Primary LLM adapter
- [x] Optional fallback adapter
- [x] Search provider interface
- [x] Safe fetcher
- [x] Extractor
- [x] Evidence selector
- [x] Planner
- [x] Synthesizer
- [x] Citation verifier
- [x] Research orchestrator
- [x] Run persistence (Postgres repository with local in-memory fallback)
- [x] Usage persistence (atomic Postgres counters with local fallback)
- [x] SSE events

## Frontend

- [x] Minimal shell
- [x] Research textarea
- [x] Keyboard submit
- [x] Research progress state
- [x] Error state
- [x] Quota state
- [x] Report renderer
- [x] Inline citations
- [x] Source rail/cards
- [x] Responsive layout
- [x] Accessibility pass (labels, live status, keyboard focus)
- [x] Supabase Auth sign-in/sign-up/sign-out
- [x] History page

## Phase 3 UX

- [x] Stage streaming telemetry
- [x] Skeleton/loading state
- [x] Citation hover/focus metadata and source highlighting
- [x] Keyboard shortcuts
- [x] Reduced-motion support
- [x] Automatic dark mode
- [x] Shareable run URL and copy-link action

## Phase 6 extras

- [x] Explainable source-quality classifier
- [x] Persisted quality score, label, and reasons
- [x] Quality signals rendered beside source cards
- [x] Quality classifier unit and pipeline tests
- [x] Bounded PDF upload and text extraction
- [x] Owner-scoped PDF evidence attached to research runs

## Database

- [x] `research_runs`
- [x] `sources`
- [x] `evidence_passages`
- [x] `run_events`
- [x] `usage_daily`
- [x] indexes
- [x] retention policy functions
- [x] ownership policy in FastAPI repository queries (RLS remains optional because the API is the DB boundary)

## Security

- [x] Secrets backend-only
- [x] SSRF private-IP block
- [x] Redirect revalidation
- [x] Body-size caps
- [x] HTML escaping
- [x] Unsafe Markdown HTML disabled (reports render structured text, never model HTML)
- [x] Auth JWT validation
- [x] Log redaction
- [x] Dependency audit (CI)

## Reliability

- [x] Provider timeout
- [x] Search timeout
- [x] Fetch timeout
- [x] Retry caps
- [x] Fallback logic
- [x] Concurrency semaphore
- [x] Idempotency handling
- [x] Run hard timeout

## Evals

- [x] 30+ cases
- [x] Completion metric
- [x] Citation validity metric
- [x] Citation coverage metric
- [x] Source diversity metric
- [x] Token usage metric
- [x] Latency metric
- [x] Regression report
- [x] CI regression gate

## Deployment

The following require the operator's hosting accounts, keys, domain, and production
environment; they cannot be completed from this repository alone.

- [ ] Frontend live
- [ ] API live
- [ ] Database live
- [ ] Custom env vars configured
- [ ] CORS production origin set
- [ ] Quotas tested in production
- [ ] Cold-start UX tested
- [ ] Public demo URL added to README
