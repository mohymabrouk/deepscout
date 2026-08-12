# Backend Specification

## 1. Stack

- Python 3.12+
- FastAPI
- Pydantic v2
- `httpx` for outbound HTTP
- SQLAlchemy 2.x or Supabase client
- Postgres
- `tiktoken` or provider-compatible tokenizer approximation where available
- `structlog` or standard JSON logging

## 2. Package layout

```text
apps/api/app/
├── main.py
├── config.py
├── api/
│   ├── deps.py
│   └── routes/
│       ├── health.py
│       ├── research.py
│       ├── runs.py
│       └── usage.py
├── core/
│   ├── errors.py
│   ├── logging.py
│   ├── security.py
│   └── rate_limit.py
├── research/
│   ├── orchestrator.py
│   ├── planner.py
│   ├── fetcher.py
│   ├── extractor.py
│   ├── evidence.py
│   ├── synthesizer.py
│   └── verifier.py
├── providers/
│   ├── llm/
│   └── search/
├── db/
│   ├── models.py
│   ├── repository.py
│   └── session.py
└── schemas/
    ├── research.py
    ├── events.py
    └── errors.py
```

## 3. Configuration

All operational limits are config, not magic constants.

```text
MAX_QUESTION_CHARS
MAX_SEARCH_QUERIES
MAX_SEARCH_RESULTS_PER_QUERY
MAX_FETCHED_PAGES
MAX_FETCH_BYTES
FETCH_TIMEOUT_SECONDS
FETCH_CONCURRENCY
MAX_EXTRACTED_CHARS_PER_SOURCE
MAX_TOTAL_CONTEXT_CHARS
MAX_LLM_CALLS_PER_RUN
MAX_INPUT_TOKENS_PER_RUN
MAX_OUTPUT_TOKENS_PER_RUN
ANON_RUNS_PER_DAY
AUTH_RUNS_PER_DAY
ANON_CONCURRENT_RUNS
AUTH_CONCURRENT_RUNS
```

## 4. Research pipeline contract

```python
async def run_research(ctx: ResearchContext) -> ResearchReport:
    budget = await budget_service.reserve(ctx.identity)
    run = await runs.create(ctx)

    try:
        plan = await planner.plan(ctx.question, budget)
        results = await searcher.search_many(plan.queries, budget)
        pages = await fetcher.fetch_bounded(results, budget)
        evidence = await evidence_selector.select(pages, ctx.question, budget)
        draft = await synthesizer.write(ctx.question, evidence, budget)
        verified = await verifier.verify_and_repair(draft, evidence, budget)
        return await runs.complete(run.id, verified, budget.usage)
    except DomainError as exc:
        await runs.fail(run.id, exc.code)
        raise
```

## 5. Structured LLM outputs

Planner response schema:

```json
{
  "queries": ["...", "..."],
  "intent": "comparison",
  "must_cover": ["pricing", "limitations"]
}
```

Final report internal schema:

```json
{
  "title": "...",
  "executive_summary": "...",
  "sections": [
    {
      "heading": "Key findings",
      "paragraphs": [
        {
          "text": "...",
          "citations": [1, 3]
        }
      ]
    }
  ],
  "limitations": ["..."]
}
```

The frontend should render from structured content. Do not ask the model to generate arbitrary HTML.

## 6. Timeouts

Suggested initial bounds:

- LLM call: 20-30 s hard timeout
- search call: 10 s
- page fetch: 8 s
- entire run: 60 s hard ceiling for synchronous MVP

All timeouts should be lower in automated tests.

## 7. Retry rules

Retry only transient classes:

- connect timeout;
- read timeout;
- HTTP 429;
- provider 5xx.

Do not retry:

- 400 validation failures;
- auth failures;
- policy rejection;
- quota rejection;
- malformed user input.

Use exponential backoff with jitter and a strict maximum attempt count.

## 8. Idempotency

Accept optional header:

```text
Idempotency-Key: <uuid>
```

For authenticated users, store the key for a short period and return the original run if the same request is resubmitted.

For anonymous demo users, frontend duplicate-submit prevention is sufficient initially, but API support is still desirable.

## 9. Logging

Every request log should include:

```text
request_id
run_id
route
identity_type
status_code
latency_ms
provider
model
llm_calls
input_tokens
output_tokens
search_calls
pages_attempted
pages_succeeded
error_code
```

Never log:

- API keys;
- auth tokens;
- full private user headers;
- raw provider credentials;
- hidden chain-of-thought.

Question text can be optionally redacted or hashed in production/demo analytics.
