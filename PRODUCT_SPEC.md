# Product Specification

## 1. Product thesis

DeepScout is a focused AI research assistant for short, source-backed web research. It is not positioned as a general chat assistant. The product should feel like a lightweight research instrument: fast, calm, transparent, and deliberate.

## 2. Target user

Primary MVP user:

- recruiter, interviewer, engineer, founder, or student evaluating the portfolio project;
- wants to ask one substantive research question;
- expects visible evidence and citations;
- will tolerate a short research wait if progress is clear;
- should never need onboarding documentation to use the app.

## 3. Jobs to be done

### Primary job

"Help me investigate a question using current web sources and give me a concise answer I can inspect."

### Secondary jobs

- compare products or technologies;
- summarize a small market landscape;
- investigate a technical topic;
- collect sources for a decision;
- revisit previous research runs.

## 4. Success metrics

### Product metrics

- Research completion rate >= 90% for supported queries
- Median time-to-first-progress event < 1.5 s
- Median total run latency target: 10-25 s depending on search/fetch latency
- Citation coverage >= 90% of material factual claims in eval set
- Fabricated-source rate = 0 in eval set
- Run hard-failure rate < 5% in demo traffic

### Cost-control metrics

- Maximum LLM calls per standard run: 3
- Default fetched pages: 6
- Maximum fetched pages: 8
- Maximum total extracted text passed to synthesis: configurable hard cap
- Per-IP and per-user daily run quotas
- Per-run token budget enforced before each model call

## 5. User stories

### US-01 Submit research

As a visitor, I can enter a question and start a research run so that I receive a source-backed report.

Acceptance criteria:

- input is 10-1,500 characters;
- whitespace-only input is rejected;
- obvious duplicate submit is suppressed while a run is active;
- UI immediately transitions into progress state;
- run receives a stable ID.

### US-02 Observe progress

As a visitor, I can see what stage the research system is in without seeing hidden chain-of-thought.

Allowed stage messages:

- Planning search
- Searching sources
- Reading sources
- Selecting evidence
- Writing report
- Verifying citations

Do not expose private model reasoning, hidden prompts, or internal scratchpad text.

### US-03 Inspect sources

As a visitor, I can inspect the sources used in the answer.

Acceptance criteria:

- every source has title, domain, URL, and retrieval timestamp;
- inline citation markers map to source cards;
- clicking a source opens the original page in a new tab;
- failed/unused fetched pages do not appear as cited sources.

### US-04 Handle limits gracefully

As a visitor, I understand when I hit a quota and what I can do next.

Acceptance criteria:

- response uses HTTP 429;
- JSON includes a stable error code;
- UI explains whether the limit is temporary, per-run, or daily;
- no silent retries that amplify cost.

## 6. Non-goals

The MVP does not claim exhaustive research, professional advice, or guaranteed factual correctness. It should visibly label itself as an AI-assisted research tool and make sources easy to verify.

## 7. Supported query policy

Good MVP queries:

- "Compare PostgreSQL pgvector and a hosted vector database for a small SaaS."
- "What are the main architectural patterns for LLM evaluation pipelines?"
- "Summarize how three major coding assistants differ for a small engineering team."

Poor MVP queries:

- requests requiring login-only sources;
- requests requiring large-scale crawling;
- real-time trading decisions;
- medical/legal diagnosis or personalized professional advice;
- requests to act on external systems.

## 8. Product states

The main screen has exactly five meaningful states:

1. Idle
2. Researching
3. Complete
4. Recoverable error
5. Quota exhausted

Avoid modal-heavy UX. State changes should happen in the main content area.
