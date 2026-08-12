-- Phase 6 source-quality signals. Apply after 002_phase5_auth_history.sql.

alter table sources
  add column if not exists quality_score real not null default 0.5,
  add column if not exists quality_label text not null default 'medium',
  add column if not exists quality_reasons jsonb not null default '[]'::jsonb;

alter table sources
  drop constraint if exists sources_quality_label_check;

alter table sources
  add constraint sources_quality_label_check
  check (quality_label in ('high', 'medium', 'low'));
