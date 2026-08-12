# Build Checklist

## Phase 1–2 implementation note

The checked implementation items below run locally against deterministic demo providers. Items involving managed persistence, authentication, deployment, or live evals are not marked complete until their external integrations are wired and validated.

## Repository

- [x] Create `apps/web`
- [x] Create `apps/api`
- [ ] Add root README
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
- [ ] Run persistence (in-memory MVP only; SQL migration exists)
- [ ] Usage persistence (in-memory MVP only)
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
- [ ] Accessibility pass (baseline semantics present; full audit remains)
- [ ] History page

## Database

- [ ] `research_runs`
- [ ] `sources`
- [ ] `evidence_passages`
- [ ] `run_events`
- [ ] `usage_daily`
- [ ] indexes
- [ ] retention policy
- [ ] ownership/RLS policy

## Security

- [ ] Secrets backend-only
- [ ] SSRF private-IP block
- [ ] Redirect revalidation
- [ ] Body-size caps
- [ ] HTML escaping
- [ ] Unsafe Markdown HTML disabled
- [ ] Auth JWT validation
- [ ] Log redaction
- [ ] Dependency audit

## Reliability

- [ ] Provider timeout
- [ ] Search timeout
- [ ] Fetch timeout
- [ ] Retry caps
- [ ] Circuit/fallback logic
- [ ] Concurrency semaphore
- [ ] Idempotency handling
- [ ] Run hard timeout

## Evals

- [ ] 30+ cases
- [ ] Completion metric
- [ ] Citation validity metric
- [ ] Citation coverage metric
- [ ] Source diversity metric
- [ ] Token usage metric
- [ ] Latency metric
- [ ] Regression report

## Deployment

- [ ] Frontend live
- [ ] API live
- [ ] Database live
- [ ] Custom env vars configured
- [ ] CORS production origin set
- [ ] Quotas tested in production
- [ ] Cold-start UX tested
- [ ] Public demo URL added to README
