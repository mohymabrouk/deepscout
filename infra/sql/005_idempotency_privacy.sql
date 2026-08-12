-- Idempotency request fingerprints. Apply after 004_operational_hardening.sql.

alter table idempotency_keys
  add column if not exists request_hash text;

create index if not exists idempotency_keys_created_idx
  on idempotency_keys(created_at);
