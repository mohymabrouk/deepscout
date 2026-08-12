# Testing Strategy

## 1. Testing pyramid

### Unit tests

Test pure logic aggressively:

- URL normalization;
- private-IP blocking;
- token budget accounting;
- citation ID validation;
- source deduplication;
- quota calculations;
- state transitions.

### Integration tests

Use fake provider adapters:

- planner -> search -> fetch -> synthesize happy path;
- provider timeout;
- provider 429;
- search failure;
- insufficient sources;
- citation repair;
- token budget exceeded.

### End-to-end tests

Frontend + API test cases:

1. submit a question;
2. observe stage updates;
3. load completed report;
4. verify source cards;
5. verify quota error rendering.

Use Playwright if desired.

## 2. Provider fakes

Never make the normal unit suite depend on live free APIs.

Create deterministic fixtures:

```python
class FakeLLMProvider:
    async def complete(self, request):
        return fixture_for(request.purpose)
```

## 3. Contract tests

Validate that each provider adapter returns the internal normalized schema regardless of vendor response shape.

## 4. Security tests

Include URLs such as:

```text
http://127.0.0.1
http://localhost
http://169.254.169.254
http://10.0.0.1
```

All must be rejected before network access.

## 5. Rate-limit tests

Verify:

- limit boundary permits final allowed request;
- next request returns 429;
- reset window works;
- authenticated and anonymous counters are independent;
- concurrent reservation is atomic.

## 6. Token-budget tests

Verify:

- oversized source context is shrunk before provider call;
- max model-call count cannot be bypassed by fallback;
- actual provider usage updates counters;
- failed provider calls are accounted according to your chosen policy.
