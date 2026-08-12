-- Operational hardening. Apply after 003_source_quality.sql.

-- Privacy mode may intentionally omit the user's question from durable storage.
alter table research_runs
  alter column question drop not null;

-- Persistent quota accounting. active_runs is a reservation counter, not a
-- historical metric; it is decremented when a run reaches a terminal state.
alter table usage_daily
  add column if not exists active_runs integer not null default 0,
  add constraint usage_daily_nonnegative_check
  check (
    research_runs >= 0 and active_runs >= 0 and llm_calls >= 0 and
    input_tokens >= 0 and output_tokens >= 0 and search_calls >= 0
  );

-- A single row per identity is updated atomically by the API for fixed-window
-- HTTP rate limiting across multiple API processes.
create table if not exists request_rate_windows (
  identity_key text primary key,
  window_started_at timestamptz not null,
  request_count integer not null default 0,
  updated_at timestamptz not null default now(),
  check (request_count >= 0)
);

-- Evidence is retained separately from the report so the report can be audited
-- without re-fetching mutable web pages.
create table if not exists evidence_passages (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references research_runs(id) on delete cascade,
  source_id uuid null references sources(id) on delete set null,
  citation_id integer not null,
  excerpt text not null,
  relevance_score real not null default 0,
  created_at timestamptz not null default now(),
  check (relevance_score >= 0)
);

create index if not exists evidence_passages_run_idx
  on evidence_passages(run_id, citation_id);

-- Run this procedure from the platform scheduler (or a protected operations
-- job) with the configured retention interval. It is deliberately explicit so
-- retention never runs unexpectedly during application startup.
create or replace function delete_expired_research_runs(retention interval)
returns bigint
language plpgsql
security invoker
set search_path = public
as $$
declare
  deleted_count bigint;
begin
  delete from research_runs
   where created_at < now() - retention;
  get diagnostics deleted_count = row_count;
  return deleted_count;
end;
$$;
