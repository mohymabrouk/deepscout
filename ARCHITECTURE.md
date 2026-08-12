# Architecture

## 1. Design principles

1. **Monolith first.** One frontend, one API service, one Postgres database.
2. **Bounded agent behavior.** The system follows a fixed research pipeline rather than an unbounded autonomous loop.
3. **Provider abstraction.** LLM and search vendors are adapters behind internal interfaces.
4. **Budget before execution.** Every external call is checked against request, token, and concurrency budgets.
5. **Evidence is a first-class object.** The final answer is built from stored source/evidence records.
6. **Observable by default.** Each stage emits structured events and timings.

## 2. High-level system

```text
Browser
  |
  v
Next.js / Vercel
  |
  | HTTPS
  v
FastAPI API
  |
  +--> Rate limiter / quota service
  +--> Research orchestrator
  |      +--> LLM provider adapter
  |      +--> Search provider adapter
  |      +--> HTTP fetcher
  |      +--> Content extractor
  |      +--> Evidence ranker
  |      +--> Citation verifier
  |
  +--> Supabase Postgres
```

## 3. Request lifecycle

```text
POST /v1/research
      |
      v
validate input
      |
      v
resolve identity key
      |
      v
check request quota + concurrency
      |
      v
create research_run row
      |
      v
planner LLM call
      |
      v
search provider
      |
      v
bounded parallel fetch
      |
      v
extract + normalize
      |
      v
rank evidence
      |
      v
synthesis LLM call
      |
      v
citation verification
      |
      v
optional repair LLM call
      |
      v
persist result + usage
      |
      v
return / stream complete
```

## 4. Internal modules

### `orchestrator`

Owns the state machine and budgets. It does not know provider-specific API details.

### `providers.llm`

Interface:

```python
class LLMProvider(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResponse: ...
```

Responsibilities:

- model mapping;
- timeout handling;
- provider-specific retries;
- normalized usage accounting;
- normalized error mapping.

### `providers.search`

Interface:

```python
class SearchProvider(Protocol):
    async def search(self, query: str, limit: int) -> list[SearchResult]: ...
```

### `fetcher`

Responsibilities:

- URL validation;
- DNS / private-network protections;
- timeout;
- redirect limit;
- max body size;
- content-type allowlist;
- bounded concurrency.

### `extractor`

Converts HTML into compact readable text. Preserve:

- title;
- headings;
- paragraphs;
- tables only when useful;
- canonical URL if available.

Remove navigation, cookie banners, repeated boilerplate, scripts, styles, and huge menus.

### `evidence`

Represents selected passages independently of final answer prose.

```text
Evidence
- evidence_id
- source_id
- excerpt
- relevance_score
- start_offset optional
- end_offset optional
```

### `citation verifier`

Checks:

- every citation ID exists;
- citations reference fetched source records;
- important factual paragraphs contain citations;
- report does not contain raw invented citation labels;
- cited source domains are returned to the frontend.

## 5. State machine

```text
PENDING
  -> PLANNING
  -> SEARCHING
  -> FETCHING
  -> SYNTHESIZING
  -> VERIFYING
  -> COMPLETED

Any active state -> FAILED
Any active state -> LIMITED
```

Persist state transitions for debugging.

## 6. Concurrency model

For the free MVP:

- one API process is acceptable;
- use async I/O;
- fetch at most 3 pages concurrently;
- enforce max 1 active research run per anonymous identity;
- enforce max 2 active runs per authenticated user;
- avoid background workers until real demand exists.

## 7. Failure policy

### Search failure

- retry once only for clearly transient errors;
- fallback provider if configured;
- otherwise terminate with `SEARCH_UNAVAILABLE`.

### Individual page failure

- mark source as fetch failed;
- continue if minimum usable source threshold can still be met.

### Primary LLM failure

- retry only on timeout/429/5xx with bounded backoff;
- fallback to secondary provider if configured and budget allows;
- never recursively retry without a hard cap.

### Citation verification failure

- perform one repair pass if token budget allows;
- otherwise return the answer with a visible "citation coverage may be incomplete" flag rather than fabricating support.
