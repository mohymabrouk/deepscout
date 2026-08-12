import Link from "next/link";
import SiteHeader from "../components/site-header";

export default function AboutPage() {
  return (
    <main className="shell">
      <SiteHeader active="about" />
      <article className="content-page about-page">
        <div className="page-intro about-intro">
          <div>
            <div className="eyebrow">About DeepScout</div>
            <h1>Research that shows its work.</h1>
            <p className="lede">DeepScout turns a focused question into a short, source-backed brief. The product is built around a simple rule: an answer is more useful when you can inspect the evidence behind it.</p>
          </div>
          <div className="intro-note">
            <span className="note-label">Built for</span>
            <p>People making a decision, learning a technical topic, or checking a claim who need a clear starting point—not a wall of generated text.</p>
          </div>
        </div>

        <section className="about-section about-principles">
          <div className="section-heading">
            <div className="eyebrow">Product principles</div>
            <h2>Useful because it stays inspectable.</h2>
          </div>
          <div className="principle-grid">
            <article><span className="principle-index">01</span><h3>Evidence before prose</h3><p>The model plans and retrieves sources before it writes. The final report is assembled from selected passages rather than an unsupported first draft.</p></article>
            <article><span className="principle-index">02</span><h3>Bounded by design</h3><p>Searches, pages, context, model calls, and output are capped per run. The limits keep the system fast enough to use and predictable enough to trust.</p></article>
            <article><span className="principle-index">03</span><h3>Claims stay traceable</h3><p>Report paragraphs carry citation IDs that map to the source list. Click a citation to move from a claim to the page that supports it.</p></article>
            <article><span className="principle-index">04</span><h3>Limitations are visible</h3><p>Missing evidence, incomplete citation coverage, and source-quality signals are shown as limitations instead of being hidden behind confident language.</p></article>
          </div>
        </section>

        <section className="about-section split-section">
          <div>
            <div className="eyebrow">What DeepScout is good at</div>
            <h2>Getting you to a reviewable first answer.</h2>
          </div>
          <div className="split-copy">
            <p>Use it for comparisons, technical explanations, market landscapes, fact checks, and questions where the first job is to gather credible starting points.</p>
            <p>Use the citations to decide what deserves a deeper read. The brief is a research surface, not a substitute for domain expertise, primary-source review, or professional advice.</p>
            <Link className="quiet-link" href="/how-it-works">See the full research pipeline <span aria-hidden="true">→</span></Link>
          </div>
        </section>

        <section className="about-section limits-section">
          <div className="eyebrow">Operating boundaries</div>
          <div className="limits-list">
            <div><strong>3</strong><span>search queries per standard run</span></div>
            <div><strong>6</strong><span>fetched pages used as source material</span></div>
            <div><strong>3</strong><span>maximum model calls per run</span></div>
            <div><strong>1</strong><span>optional PDF attachment per run</span></div>
          </div>
          <p className="section-footnote">These defaults are guardrails, not a claim that every question can be answered completely. If the available evidence is thin, the report should say so.</p>
        </section>

        <div className="page-cta">
          <div>
            <div className="eyebrow">Start here</div>
            <h2>Ask a question you can actually act on.</h2>
          </div>
          <Link className="primary link-button" href="/">New research <span aria-hidden="true">→</span></Link>
        </div>
      </article>
    </main>
  );
}
