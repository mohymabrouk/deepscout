# Environment Variables

Use `.env.example` as the canonical template. The API reads `.env` from the repository
working directory; the frontend reads `apps/web/.env.local`.

```dotenv
# App
APP_ENV=development
APP_VERSION=0.1.0
FRONTEND_ORIGIN=http://localhost:3000
API_PUBLIC_URL=http://localhost:8000

# Database / Supabase Auth
DATABASE_URL=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
SUPABASE_JWT_JWKS_URL=
SUPABASE_JWT_AUDIENCE=authenticated

# Frontend-safe Supabase Auth settings
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=

# LLM primary
LLM_PROVIDER=demo
LLM_API_KEY=
LLM_MODEL=demo
LLM_TIMEOUT_SECONDS=25

# LLM fallback
LLM_FALLBACK_ENABLED=true
LLM_FALLBACK_PROVIDER=openrouter
LLM_FALLBACK_API_KEY=
LLM_FALLBACK_MODEL=

# Search
SEARCH_PROVIDER=demo
SEARCH_API_KEY=
SEARCH_TIMEOUT_SECONDS=10

# Identity / abuse controls
ANON_ID_HMAC_SECRET=
ANON_RUNS_PER_DAY=5
AUTH_RUNS_PER_DAY=15
ANON_CONCURRENT_RUNS=1
AUTH_CONCURRENT_RUNS=2
HTTP_REQUESTS_PER_MINUTE_ANON=10
HTTP_REQUESTS_PER_MINUTE_AUTH=30

# Run budgets
MAX_QUESTION_CHARS=1500
MAX_SEARCH_QUERIES=3
MAX_SEARCH_RESULTS_PER_QUERY=5
MAX_FETCHED_PAGES=6
MAX_FETCH_BYTES=3000000
FETCH_TIMEOUT_SECONDS=8
FETCH_CONCURRENCY=3
MAX_EXTRACTED_CHARS_PER_SOURCE=12000
MAX_TOTAL_CONTEXT_CHARS=50000
MAX_LLM_CALLS_PER_RUN=3
MAX_INPUT_TOKENS_PER_RUN=18000
MAX_OUTPUT_TOKENS_PER_RUN=2500
MAX_REQUEST_BYTES=64000
MAX_DOCUMENT_BYTES=10000000
MAX_DOCUMENT_PAGES=50
MAX_DOCUMENT_CHARS=100000
MAX_DOCUMENTS_PER_RUN=3

# Logging
LOG_LEVEL=INFO
STORE_QUESTION_TEXT=false

# Feature flags
ENABLE_AUTH=false
ENABLE_HISTORY=true
ENABLE_FALLBACK_PROVIDER=true
ENABLE_DEBUG_USAGE=false
```

## Rules

- `.env` files are ignored by Git.
- `.env.example` contains no real keys.
- leave both providers set to `demo` for a complete local run without paid services.
- set `LLM_PROVIDER=groq` or `openrouter` and `SEARCH_PROVIDER=brave` only after adding keys.
- never put `SUPABASE_SERVICE_ROLE_KEY`, provider keys, JWT secrets, or HMAC secrets in the frontend environment.
- production secrets are configured in hosting dashboards.
- fallback provider can be disabled without code changes.
- all quotas can be reduced immediately if abuse appears.
