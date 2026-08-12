# DeepScout evaluations

The normal evaluation suite is deterministic and never calls a paid provider. It runs the complete orchestrator with the demo search/LLM adapters, then measures behavior from the run record.

```bash
.venv/bin/python evals/run_eval.py \
  --cases evals/cases.jsonl \
  --output /tmp/deepscout-eval.json \
  --baseline evals/baselines/demo.json \
  --fail-on-regression
```

The runner reports per-case and aggregate metrics for completion, latency, token usage, model calls, fetched pages, citation coverage, invalid citation IDs, URL integrity, source diversity, retrieval sufficiency, concept coverage, and fallback usage.

The checked-in baseline is intentionally tied to the deterministic demo provider. Its latency and token figures are smoke-test measurements, not production capacity claims. Live-provider evaluation should use a separate baseline and explicit credentials outside CI.

The first measured adapter improvement is recorded in [`benchmarks/demo-v2.json`](benchmarks/demo-v2.json): concept coverage increased from 5.2% to 14.6% (+9.375 percentage points), while median total tokens increased 7.88%, below the 20% gate.

Regression gates:

- invalid citation case rate must not increase;
- completion rate may not fall by more than five percentage points;
- median total token usage may not increase by more than twenty percent.
