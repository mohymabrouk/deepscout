create extension if not exists pgcrypto;

create table if not exists research_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid null,
  anonymous_key text null,
  question text not null,
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

create index if not exists research_runs_user_created_idx on research_runs(user_id, created_at desc);
create index if not exists research_runs_anon_created_idx on research_runs(anonymous_key, created_at desc);

create table if not exists sources (
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
  extracted_text text null,
  content_hash text null,
  created_at timestamptz not null default now(),
  unique(run_id, url)
);

create table if not exists usage_daily (
  identity_key text not null,
  usage_date date not null,
  research_runs integer not null default 0,
  llm_calls integer not null default 0,
  input_tokens bigint not null default 0,
  output_tokens bigint not null default 0,
  search_calls integer not null default 0,
  primary key(identity_key, usage_date)
);

