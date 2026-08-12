# API Specification

Base path: `/v1`

## 1. `GET /health`

Response:

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

Do not call external providers from the basic health endpoint.

## 2. `GET /ready`

Checks required dependencies with short timeouts.

Response:

```json
{
  "status": "ready",
  "database": true
}
```

Provider readiness should be optional to avoid burning API calls.

## 3. `POST /v1/research`

Request:

```json
{
  "question": "Compare pgvector and hosted vector databases for a small SaaS.",
  "mode": "standard"
}
```

Headers:

```text
Content-Type: application/json
Authorization: Bearer <optional Supabase JWT>
Idempotency-Key: <optional uuid>
```

When enabled, the API accepts only a Supabase access token signed with the configured
JWT secret, issuer/audience, expiry, UUID subject, and `role=authenticated`. The server
derives ownership from the token `sub` claim; request bodies never select a user.

Success: `202 Accepted`

```json
{
  "run_id": "run_01...",
  "status": "pending",
  "events_url": "/v1/research/run_01.../events"
}
```

## 4. `GET /v1/research/{run_id}/events`

SSE event examples:

```text
event: stage
data: {"stage":"searching","message":"Searching sources","sources_found":7}

event: stage
data: {"stage":"fetching","message":"Reading sources","completed":4,"total":6}

event: complete
data: {"run_id":"run_01...","status":"completed"}
```

No chain-of-thought or raw prompt content is emitted.

## 5. `GET /v1/research/{run_id}`

Response:

```json
{
  "id": "run_01...",
  "status": "completed",
  "question": "...",
  "report": {
    "title": "...",
    "executive_summary": "...",
    "sections": [],
    "limitations": []
  },
  "sources": [
    {
      "citation_id": 1,
      "title": "...",
      "url": "https://example.com/...",
      "domain": "example.com",
      "retrieved_at": "2026-08-12T10:00:00Z"
    }
  ],
  "usage": {
    "input_tokens": 4300,
    "output_tokens": 1100,
    "llm_calls": 3
  }
}
```

Usage may be hidden from normal users and visible only in debug/admin mode.

## 6. `GET /v1/runs`

Authenticated only.

Query params:

```text
limit=20
cursor=<opaque>
```

Returns compact run metadata, not all source text.

## 7. `DELETE /v1/runs/{run_id}`

Authenticated or anonymous owner only. Deletes the run and its sources/events through
the database foreign-key cascade. A run owned by another user is indistinguishable from
a missing run and returns `404`.

## 8. `GET /v1/usage`

Response:

```json
{
  "period": "day",
  "runs_used": 3,
  "runs_limit": 10,
  "input_tokens_used": 12000,
  "input_tokens_limit": 50000,
  "resets_at": "2026-08-13T00:00:00Z"
}
```

## 8. Error format

All domain errors use:

```json
{
  "error": {
    "code": "DAILY_RUN_LIMIT",
    "message": "Daily demo run limit reached.",
    "request_id": "req_01...",
    "retry_after_seconds": 1800
  }
}
```

Stable error codes:

```text
INVALID_REQUEST
QUESTION_TOO_LONG
DAILY_RUN_LIMIT
TOKEN_BUDGET_EXCEEDED
CONCURRENCY_LIMIT
PROVIDER_RATE_LIMIT
PROVIDER_UNAVAILABLE
HTTP_RATE_LIMIT
SEARCH_UNAVAILABLE
INSUFFICIENT_SOURCES
RUN_TIMEOUT
RUN_NOT_FOUND
UNAUTHORIZED
INTERNAL_ERROR
```

## 9. HTTP semantics

- `200` successful reads
- `202` run accepted
- `400` invalid user request
- `401` auth required
- `404` run not found / not visible
- `409` duplicate idempotency conflict if necessary
- `422` schema validation
- `429` quota or rate limit
- `503` upstream provider unavailable

Prefer explicit domain error codes over interpreting status alone.
