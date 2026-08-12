# Deployment

## 1. Goal

Deploy a publicly accessible demo with the smallest operational footprint possible.

Recommended topology:

```text
GitHub
  |
  +--> Vercel: Next.js frontend
  |
  +--> Render/free container host: FastAPI
              |
              +--> Supabase Postgres/Auth
              +--> LLM API
              +--> Search API
```

## 2. Frontend deployment

Environment variables:

```text
NEXT_PUBLIC_API_BASE_URL=https://api.example.com
NEXT_PUBLIC_SUPABASE_URL=<optional>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<optional>
```

Only variables explicitly safe for browser exposure may use `NEXT_PUBLIC_`.

## 3. Backend deployment

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Environment (backend):

```text
APP_ENV=production
DATABASE_URL=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=... # legacy HS256 only; omit when using JWKS
SUPABASE_JWT_JWKS_URL=... # usually <SUPABASE_URL>/auth/v1/.well-known/jwks.json
SUPABASE_JWT_AUDIENCE=authenticated
LLM_PROVIDER=groq
LLM_API_KEY=...
LLM_MODEL=...
LLM_FALLBACK_PROVIDER=openrouter
LLM_FALLBACK_API_KEY=...
SEARCH_PROVIDER=...
SEARCH_API_KEY=...
ANON_ID_HMAC_SECRET=...
FRONTEND_ORIGIN=https://...
```

## 4. Free-host cold starts

Some free hosts sleep idle services.

Design for it:

- frontend should show `Connecting to research service...` after a threshold;
- API startup should not run migrations or heavy model loading;
- use managed external Postgres;
- keep import-time work minimal.

Cold start is acceptable for a portfolio demo if UX communicates it.

## 5. Migrations

Use the checked-in SQL migration files.

Deployment rule:

- migrations run explicitly, not at every app boot;
- destructive migrations require backup/confirmation;
- schema version is logged on startup.

Apply `infra/sql/001_initial.sql` through `infra/sql/006_pdf_documents.sql` in order
before setting `DATABASE_URL` on the API service.

## 6. CI/CD

GitHub Actions pipeline:

```text
frontend lint
frontend typecheck
frontend tests
backend lint
backend tests
security/dependency audit
build
```

Vercel/Render can deploy automatically after main branch passes checks.

## 7. Production checklist

- [ ] frontend and API on HTTPS
- [ ] CORS restricted
- [ ] provider secrets backend-only
- [ ] database RLS/access policy reviewed
- [ ] anonymous quotas enabled
- [ ] token budgets enabled
- [ ] fetch SSRF protections enabled
- [ ] log redaction enabled
- [ ] `/health` working
- [ ] error tracking verified
- [ ] at least 20 eval cases passing
- [ ] README demo URL added
