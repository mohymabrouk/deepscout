# Search, Retrieval & Evidence

## 1. Search strategy

The planner returns 2-4 complementary queries. The search layer merges results and deduplicates URLs.

Ranking priorities:

1. direct relevance;
2. source authority;
3. recency when the question is time-sensitive;
4. diversity of domains;
5. primary sources where possible.

## 2. URL normalization

Normalize for deduplication:

- lowercase hostname;
- remove fragments;
- remove common tracking params;
- normalize trailing slash conservatively;
- preserve meaningful query params.

Common removable tracking parameters:

```text
utm_source
utm_medium
utm_campaign
utm_term
utm_content
gclid
fbclid
```

## 3. Fetching

Use `httpx.AsyncClient` with:

- explicit user-agent;
- connect/read timeouts;
- redirect cap;
- streaming body with byte cap;
- SSRF-safe DNS/IP validation.

Supported initial content types:

```text
text/html
text/plain
application/xhtml+xml
```

PDF support can be added later because robust PDF parsing adds complexity.

## 4. Extraction

Aim for readable text, not perfect DOM preservation.

Possible implementation choices:

- `trafilatura`;
- `readability-lxml`;
- a small custom BeautifulSoup pipeline.

Store title and extracted body separately.

## 5. Deduplication

Calculate `content_hash` on normalized extracted text.

If two sources are near-identical syndicated copies:

- keep the more authoritative/original domain when identifiable;
- avoid passing both to synthesis.

## 6. Evidence selection

For MVP, embeddings are optional.

Simple path:

1. split each source into paragraph-sized chunks;
2. keyword/BM25-ish scoring against question and `must_cover` terms;
3. optionally use one lightweight LLM classification pass only if within budget;
4. select a diverse set across sources.

Goal: keep synthesis context small and evidence-dense.

## 7. Source diversity rule

Default target:

- minimum usable sources: 3;
- ideal: 4-6;
- maximum sent to synthesis: 6.

Avoid letting one domain dominate unless it is clearly the canonical primary source.

## 8. Recency

If query intent is time-sensitive:

- search provider should favor recent results;
- preserve published dates only when reliably available;
- synthesis should not infer dates from retrieval timestamps.

## 9. Retrieval quality metrics

Track in evals:

```text
usable_sources
unique_domains
primary_source_fraction
failed_fetch_fraction
evidence_relevance_score
citation_source_precision
```
