-- Phase 5 run history storage. Apply after 001_initial.sql.

alter table research_runs
  add column if not exists stage_timings jsonb not null default '[]'::jsonb,
  add column if not exists provider_names jsonb not null default '[]'::jsonb,
  add column if not exists fallback_used boolean not null default false;

create table if not exists run_events (
  id bigint generated always as identity primary key,
  run_id uuid not null references research_runs(id) on delete cascade,
  event_type text not null,
  stage text null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists run_events_run_id_idx on run_events(run_id, id);

create table if not exists idempotency_keys (
  identity_key text not null,
  idempotency_key text not null,
  run_id uuid not null references research_runs(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key(identity_key, idempotency_key)
);

create index if not exists research_runs_user_cursor_idx
  on research_runs(user_id, created_at desc, id desc);
