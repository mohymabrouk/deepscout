import Link from "next/link";
import SiteHeader from "../components/site-header";

const stages = [
  {
    id: "01",
    name: "Request admission",
    code: "POST /v1/research",
    detail: "The API validates the request before any provider call. The question must be at least 10 characters and no more than 1,500 characters. The mode is currently standard and the request can reference up to three uploaded documents.",
    mechanics: [
      "The middleware derives an anonymous HMAC identity from the client network or verifies a Supabase bearer token.",
      "Per-minute request limits and the daily run quota are reserved before the job is accepted.",
      "An optional Idempotency-Key maps retries to the original run instead of creating a duplicate job.",
    ],
    output: "HTTP 202 with run_id and events_url",
  },
  {
    id: "02",
    name: "Plan the search",
    code: "Planner.complete()",
    detail: "The first model call is not asked to answer the question. It must return JSON containing queries, intent, and must_cover. The planner output is deduplicated and truncated to the configured query limit.",
    mechanics: [
      "Default maximum: 3 search queries per run.",
      "The same RunBudget reserves input and output tokens before the provider call.",
      "Invalid JSON or an empty query list stops the run with a planner error.",
    ],
    output: "PlannerResult(queries, intent, must_cover)",
  },
  {
    id: "03",
    name: "Retrieve candidates",
    code: "SearchProvider.search()",
    detail: "The provider adapter hides vendor-specific HTTP details behind one interface. With Brave configured, each query calls the web search endpoint and returns URL, title, snippet, and domain fields.",
    mechanics: [
      "Default maximum: 5 results per query, up to 15 candidates before deduplication.",
      "Transient provider failures are retried by ReliableSearchProvider.",
      "Identical URLs are removed before page fetching; search calls are counted per query.",
    ],
    output: "A deduplicated list of SearchResult objects",
  },
  {
    id: "04",
    name: "Fetch and sanitize pages",
    code: "SafeFetcher.fetch_many()",
    detail: "Search snippets are not evidence. The fetcher opens the candidate pages, validates every URL and redirect, streams the response under a byte limit, and extracts readable text.",
    mechanics: [
      "Only public HTTP(S) hosts are allowed; DNS results are checked to block private or loopback addresses.",
      "Only HTML, XHTML, and plain text responses are accepted. Scripts, styles, navigation, forms, SVG, and footers are removed.",
      "Default guardrails: 6 pages, 3 concurrent fetches, 8-second timeout, and 3 MB per response.",
    ],
    output: "FetchedPage(url, title, text, domain, status_code)",
  },
  {
    id: "05",
    name: "Select evidence",
    code: "EvidenceSelector.select()",
    detail: "The selector splits page text into paragraphs, scores each paragraph by token overlap with the question and planner requirements, and keeps the strongest excerpts.",
    mechanics: [
      "The selector ranks passages by overlap between normalized question terms and passage terms.",
      "It prefers domain diversity: up to three different domains are selected before filling remaining slots.",
      "Default context ceiling: 50,000 characters across at most 6 evidence passages.",
    ],
    output: "EvidencePassage(source_index, excerpt, relevance_score)",
  },
  {
    id: "06",
    name: "Synthesize a report",
    code: "Synthesizer.synthesize()",
    detail: "The second model call receives the original question plus XML-delimited evidence blocks. It is instructed to return the report contract, not to browse or invent sources.",
    mechanics: [
      "The adapter sends an OpenAI-compatible chat-completions request with JSON-object response format.",
      "The report shape is title, executive_summary, sections, paragraphs, citations, and limitations.",
      "Default run budget: 3 model calls, 18,000 input tokens, and 2,500 output tokens across the run.",
    ],
    output: "ResearchReport validated by Pydantic",
  },
  {
    id: "07",
    name: "Verify and persist",
    code: "CitationVerifier + Repository",
    detail: "The verifier compares every citation ID against the evidence actually selected. Unknown IDs are removed, missing citation coverage is added to limitations, and only then is the completed report stored.",
    mechanics: [
      "The browser receives stage, complete, and error events over Server-Sent Events at /events.",
      "Local runs use the in-memory repository; DATABASE_URL switches the app to the Postgres repository.",
      "History queries are owner-scoped and require a signed-in user; deletion cancels an active task when possible.",
    ],
    output: "completed RunRecord with report, sources, usage, and metrics",
  },
];

const contracts = [
  ["POST /v1/research", "Accepts a question and optional document IDs; returns 202 immediately."],
  ["GET /v1/research/{id}", "Returns the current run status, report, sources, usage, or error code."],
  ["GET /v1/research/{id}/events", "Streams stage changes until completed, failed, or limited."],
  ["GET /v1/runs", "Lists completed history for the authenticated owner with cursor pagination."],
];

const failureModes = [
  ["No usable pages", "Search may return URLs that block automated fetches, time out, or return unsupported content. The run fails with INSUFFICIENT_SOURCES when no usable evidence remains."],
  ["Provider failure", "Transient search or model errors are retried within the configured retry count. A persistent provider failure becomes a controlled provider error rather than an unhandled exception."],
  ["Budget exhaustion", "Input, output, and model-call reservations are checked before every model call. Exceeding a run budget produces TOKEN_BUDGET_EXCEEDED and stops further work."],
  ["Invalid model output", "Planner and report JSON are validated. A report that cannot be parsed or normalized is reported as SYNTHESIS_INVALID; it is not mislabeled as missing sources."],
];

export default function HowItWorksPage() {
  return (
    <main className="shell">
      <SiteHeader active="how-it-works" />
      <section className="content-page technical-page">
        <div className="page-intro technical-intro">
          <div>
            <div className="eyebrow">System walkthrough</div>
            <h1>What happens inside a research run.</h1>
            <p className="lede">This is the implementation path—not a marketing summary. Every run moves through the same bounded pipeline, and every stage has a contract, a limit, and a failure mode.</p>
          </div>
          <div className="intro-note technical-note">
            <span className="note-label">Execution model</span>
            <code>FastAPI → async task → SSE events</code>
            <p>The request returns immediately with a run ID. The worker updates the run record while the browser listens for stage events.</p>
          </div>
        </div>

        <section className="tech-section tech-flow-section">
          <div className="tech-section-heading">
            <div className="eyebrow">Control flow</div>
            <h2>The complete path</h2>
          </div>
          <div className="tech-flow" aria-label="Research run control flow">
            <span>Browser</span><b>→</b><span>FastAPI route</span><b>→</b><span>Async run task</span><b>→</b><span>Planner</span><b>→</b><span>Search + fetch</span><b>→</b><span>Evidence</span><b>→</b><span>Synthesis</span><b>→</b><span>Verify + store</span>
          </div>
          <p className="tech-caption"><code>POST /v1/research</code> creates the run; <code>GET /v1/research/{"{run_id}"}/events</code> exposes progress; the final record is read through <code>GET /v1/research/{"{run_id}"}</code>.</p>
        </section>

        <section className="tech-section">
          <div className="tech-section-heading">
            <div className="eyebrow">Pipeline stages</div>
            <h2>What each stage receives, does, and returns.</h2>
          </div>
          <div className="technical-steps">
            {stages.map((stage) => (
              <article className="technical-step" key={stage.id}>
                <div className="technical-step-index">{stage.id}</div>
                <div className="technical-step-main">
                  <div className="technical-step-title"><h3>{stage.name}</h3><code>{stage.code}</code></div>
                  <p>{stage.detail}</p>
                  <ul>{stage.mechanics.map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
                <div className="technical-output"><span className="note-label">Returns</span><code>{stage.output}</code></div>
              </article>
            ))}
          </div>
        </section>

        <section className="tech-section">
          <div className="tech-section-heading">
            <div className="eyebrow">HTTP and storage contracts</div>
            <h2>The interfaces that connect the system.</h2>
          </div>
          <div className="contract-list">
            {contracts.map(([endpoint, description]) => <div className="contract-row" key={endpoint}><code>{endpoint}</code><p>{description}</p></div>)}
          </div>
          <div className="implementation-grid">
            <article><span className="note-label">Provider abstraction</span><p><code>LLMProvider</code> and <code>SearchProvider</code> are internal protocols. Groq uses the OpenAI-compatible adapter; Brave uses the search adapter. The orchestrator does not depend on vendor-specific response objects.</p></article>
            <article><span className="note-label">Run state</span><p>Statuses move through <code>pending → planning → searching → fetching → selecting → synthesizing → verifying → completed</code>. Failures preserve an explicit error code and emit an error event.</p></article>
            <article><span className="note-label">Ownership</span><p>Every run carries an identity key. Repository reads, uploaded documents, history listing, and deletion are checked against that identity or the authenticated user ID.</p></article>
          </div>
        </section>

        <section className="tech-section">
          <div className="tech-section-heading">
            <div className="eyebrow">Failure semantics</div>
            <h2>What can stop a run, and why.</h2>
          </div>
          <div className="failure-list">
            {failureModes.map(([name, description]) => <article key={name}><strong>{name}</strong><p>{description}</p></article>)}
          </div>
        </section>

        <section className="technical-boundaries">
          <div>
            <div className="eyebrow">Read the result correctly</div>
            <h2>Source-backed does not mean automatically true.</h2>
          </div>
          <div className="technical-boundary-copy">
            <p>DeepScout proves that a report paragraph points to a page that was fetched and selected. It does not prove that the page is authoritative, current, unbiased, or correct.</p>
            <p>Use the source title, domain, quality signals, excerpt context, and limitations to decide what to verify next. For consequential decisions, open the original source and check it yourself.</p>
          </div>
        </section>

        <div className="page-cta">
          <div>
            <div className="eyebrow">Inspect the output</div>
            <h2>Run the pipeline on a real question.</h2>
          </div>
          <Link className="primary link-button" href="/">New research <span aria-hidden="true">→</span></Link>
        </div>
      </section>
    </main>
  );
}
