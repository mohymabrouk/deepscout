# Build Checklist

## Repository

- [ ] Create `apps/web`
- [ ] Create `apps/api`
- [ ] Add root README
- [ ] Add `.env.example`
- [ ] Add CI
- [ ] Protect `main` branch if desired

## Backend

- [ ] Config validation
- [ ] Health endpoint
- [ ] Error schema
- [ ] Request ID middleware
- [ ] CORS
- [ ] Rate limiter
- [ ] Run budget manager
- [ ] LLM provider interface
- [ ] Primary LLM adapter
- [ ] Optional fallback adapter
- [ ] Search provider interface
- [ ] Safe fetcher
- [ ] Extractor
- [ ] Evidence selector
- [ ] Planner
- [ ] Synthesizer
- [ ] Citation verifier
- [ ] Research orchestrator
- [ ] Run persistence
- [ ] Usage persistence
- [ ] SSE events

## Frontend

- [ ] Minimal shell
- [ ] Research textarea
- [ ] Keyboard submit
- [ ] Research progress state
- [ ] Error state
- [ ] Quota state
- [ ] Report renderer
- [ ] Inline citations
- [ ] Source rail/cards
- [ ] Responsive layout
- [ ] Accessibility pass
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
