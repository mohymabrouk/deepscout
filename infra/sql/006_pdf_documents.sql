-- PDF upload and ingestion storage. Apply after 005_idempotency_privacy.sql.

create table if not exists user_documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid null,
  anonymous_key text null,
  filename text not null,
  extracted_text text not null,
  page_count integer not null default 0,
  content_hash text not null,
  created_at timestamptz not null default now(),
  check ((user_id is not null) <> (anonymous_key is not null)),
  check (page_count >= 0)
);

create index if not exists user_documents_user_created_idx
  on user_documents(user_id, created_at desc);

create index if not exists user_documents_anon_created_idx
  on user_documents(anonymous_key, created_at desc);

create or replace function delete_expired_documents(retention interval)
returns bigint
language plpgsql
security invoker
set search_path = public
as $$
declare
  deleted_count bigint;
begin
  delete from user_documents
   where created_at < now() - retention;
  get diagnostics deleted_count = row_count;
  return deleted_count;
end;
$$;
