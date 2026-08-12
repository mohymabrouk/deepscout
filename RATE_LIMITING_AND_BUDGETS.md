# Rate Limiting & Token Budgets

This is a core part of the MVP because the app is intended to run on free or very small provider allowances.

## 1. Goals

Protect against:

- accidental refresh loops;
- a user repeatedly clicking submit;
- bots draining inference quota;
- unexpectedly large prompts;
- runaway agent loops;
- provider rate-limit cascades;
- excessive page fetching.

## 2. Identity keys

Use the strongest available identity:

```text
authenticated user -> user_id
anonymous visitor  -> privacy-preserving IP-derived key
```

Recommended anonymous key:

```text
HMAC(server_secret, normalized_ip_prefix)
```

Do not store raw IP longer than operationally necessary.

If behind Vercel/Render/proxy infrastructure, only trust forwarding headers from known proxy configuration.

## 3. Limit layers

Use multiple independent limits.

### Layer A: HTTP burst limit

Example:

```text
anonymous:     10 requests / minute / identity
authenticated: 30 requests / minute / user
```

This covers all API traffic, not just research runs.

### Layer B: research creation limit

Example demo defaults:

```text
anonymous:      5 runs / day
authenticated: 15 runs / day
```

### Layer C: concurrency limit

```text
anonymous:      1 active run
authenticated:  2 active runs
```

### Layer D: per-run LLM call budget

```text
standard mode: max 3 model calls
```

Recommended call allocation:

1. planning;
2. synthesis;
3. optional citation repair.

If verification can be deterministic, skip call #3.

### Layer E: token budget

Track separately:

```text
max_input_tokens_per_run
max_output_tokens_per_run
max_total_tokens_per_day
```

Illustrative demo defaults:

```text
input per run:   18,000
output per run:   2,500
input per day:   70,000 anonymous
output per day:  10,000 anonymous
```

Tune these to the actual provider free limits and model context window.

## 4. Budget object

Use a request-scoped budget manager.

```python
@dataclass
class RunBudget:
    max_llm_calls: int
    max_input_tokens: int
    max_output_tokens: int
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def assert_can_call(self, estimated_input: int, requested_output: int) -> None:
        if self.llm_calls + 1 > self.max_llm_calls:
            raise TokenBudgetExceeded("LLM call budget exceeded")
        if self.input_tokens + estimated_input > self.max_input_tokens:
            raise TokenBudgetExceeded("Input token budget exceeded")
        if self.output_tokens + requested_output > self.max_output_tokens:
            raise TokenBudgetExceeded("Output token budget exceeded")
```

After provider response, replace estimates with actual usage when the provider exposes it.

## 5. Preflight token estimation

Before each model call:

1. serialize final prompt/messages;
2. estimate tokens with the closest available tokenizer;
3. reserve output allowance;
4. reject or shrink context before calling the provider.

Context-shrinking order:

1. remove duplicate passages;
2. reduce per-source excerpt size;
3. reduce number of evidence passages;
4. reduce number of sources;
5. ask user to narrow the question if still over budget.

Never send the oversized prompt and hope the provider rejects it.

## 6. Fetch budgets

Suggested limits:

```text
search queries/run:       3
results/query:            5
unique candidate URLs:   12
pages fetched:            6 normal / 8 hard max
fetch concurrency:        3
max response body:        2-4 MB/page
max extracted chars:      12k/source
max total evidence chars: 40k-60k
```

## 7. Persistence strategy

For a single-instance free MVP, Postgres-backed counters are sufficient.

Tables:

```text
usage_daily
- identity_key
- usage_date
- research_runs
- llm_calls
- input_tokens
- output_tokens
- search_calls
```

Use atomic SQL updates.

If the app later scales to multiple high-throughput instances, introduce Redis for fast fixed-window/sliding-window counters.

## 8. Atomic quota reservation

Prefer reservation over after-the-fact accounting.

Pseudo-SQL concept:

```sql
UPDATE usage_daily
SET research_runs = research_runs + 1
WHERE identity_key = :identity
  AND usage_date = CURRENT_DATE
  AND research_runs < :daily_limit
RETURNING research_runs;
```

If no row returns, reject with `429 DAILY_RUN_LIMIT`.

For first usage of a day, insert with an upsert strategy.

## 9. Provider-side limits

Treat provider 429 independently from user limits.

Provider limiter should have:

- global semaphore;
- requests-per-minute guard where needed;
- retry-after parsing;
- circuit breaker after repeated failures;
- fallback provider only if configured.

Do not expose provider quota numbers to users unless intentional.

## 10. Abuse controls

Minimum controls:

- question length cap;
- URL fetch allowlist by scheme (`http`, `https` only);
- block localhost/private network targets;
- user-agent on outbound fetches;
- hard redirect count;
- content-type checks;
- daily identity quota;
- bot protection at CDN layer if abuse appears.

## 11. UX headers

Useful response headers:

```text
X-RateLimit-Limit
X-RateLimit-Remaining
X-RateLimit-Reset
Retry-After
```

Do not depend on headers alone; return structured JSON errors too.
