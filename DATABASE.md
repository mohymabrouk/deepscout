# Database Schema

Postgres is the system of record.

## 1. `research_runs`

```sql
create table research_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid null,
  anonymous_key text null,
  question text null,
  status text not null,
  stage text null,
  report jsonb null,
  error_code text null,
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  llm_calls integer not null default 0,
  search_calls integer not null default 0,
  pages_attempted integer not null default 0,
  pages_succeeded integer not null default 0,
  started_at timestamptz not null default now(),
  completed_at timestamptz null,
  created_at timestamptz not null default now()
);
```

Indexes:

```sql
create index research_runs_user_created_idx
  on research_runs(user_id, created_at desc);

create index research_runs_anon_created_idx
  on research_runs(anonymous_key, created_at desc);
```

## 2. `sources`

```sql
create table sources (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references research_runs(id) on delete cascade,
  citation_id integer null,
  url text not null,
  canonical_url text null,
  domain text not null,
  title text null,
  fetched_at timestamptz null,
  fetch_status text not null,
  http_status integer null,
  content_type text null,
  quality_score real not null default 0.5,
  quality_label text not null default 'medium',
  quality_reasons jsonb not null default '[]'::jsonb,
  extracted_text text null,
  content_hash text null,
  created_at timestamptz not null default now(),
  unique(run_id, url)
);
```

## 3. `evidence_passages`

```sql
create table evidence_passages (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references research_runs(id) on delete cascade,
  source_id uuid null references sources(id) on delete set null,
  citation_id integer not null,
  excerpt text not null,
  relevance_score real not null default 0,
  created_at timestamptz not null default now()
);
```

For a privacy-minimized demo, consider deleting `extracted_text` and `evidence_passages` after a retention period while keeping URLs and final reports.

## 4. `run_events`

Persisted event stream used by the research UI and API diagnostics.

```sql
create table run_events (
  id bigint generated always as identity primary key,
  run_id uuid not null references research_runs(id) on delete cascade,
  event_type text not null,
  stage text null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

## 5. `usage_daily`

```sql
create table usage_daily (
  identity_key text not null,
  usage_date date not null,
  research_runs integer not null default 0,
  llm_calls integer not null default 0,
  input_tokens bigint not null default 0,
  output_tokens bigint not null default 0,
  search_calls integer not null default 0,
  active_runs integer not null default 0,
  primary key(identity_key, usage_date)
);
```

## 6. `idempotency_keys`

```sql
create table idempotency_keys (
  identity_key text not null,
  idempotency_key text not null,
  run_id uuid not null references research_runs(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key(identity_key, idempotency_key)
);
```

## 7. `request_rate_windows`

Atomic fixed-window request counters used when the API runs with Postgres and multiple
workers.

## 8. `user_documents`

Owner-scoped PDF metadata and bounded extracted text. Documents are referenced by ID in
`POST /v1/research`; callers cannot attach another user's document.

## 9. Retention functions

`delete_expired_research_runs(interval)` and `delete_expired_documents(interval)` are
explicit scheduler-facing functions. They do not run automatically at API startup.
```

## 10. Row-level security

If exposing Supabase directly to the frontend for history reads:

- enable RLS;
- users can only read rows where `user_id = auth.uid()`;
- never allow frontend writes to usage counters;
- service-role key remains backend-only.

Phase 5 uses the latter model: the API's Postgres repository applies `user_id` ownership
predicates and the browser never connects with a service-role credential. Apply
`infra/sql/002_phase5_auth_history.sql` after the initial schema; it adds persisted event
streams, metrics JSON, idempotency storage, and the stable history cursor index.

Apply `infra/sql/003_source_quality.sql` after the Phase 5 migration to add the persisted
quality score, bounded label, and explainable reason list. Apply migrations 004–006 for
atomic operational counters, evidence/retention functions, idempotency privacy metadata,
and owner-scoped PDF documents.

## 11. Retention

Suggested demo retention:

```text
anonymous full run data: 7 days
anonymous aggregate usage: 30 days
user-owned history: until user deletes or project policy changes
raw extracted source text: shortest practical period
```

Document the actual policy in `/about` or privacy copy.
