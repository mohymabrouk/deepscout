import Link from "next/link";

export default function HomePage() {
  return (
    <main className="shell">
      <header className="header">
        <Link className="wordmark" href="/">DeepScout</Link>
        <nav className="nav" aria-label="Primary navigation">
          <Link href="/about">About</Link>
        </nav>
      </header>
      <section className="hero">
        <div className="eyebrow">Research with evidence</div>
        <h1>Ask a focused question. Get a brief you can inspect.</h1>
        <p className="lede">DeepScout searches, reads, and returns a concise source-backed answer.</p>
        <div className="composer" aria-label="Research question">
          <textarea aria-label="Research question" placeholder="What would you like to investigate?" />
          <div className="composer-footer">
            <span className="hint">Cmd/Ctrl + Enter to research</span>
            <button className="primary" type="button">Research</button>
          </div>
        </div>
        <div className="examples" aria-label="Example questions">
          <span>Try:</span>
          <button type="button">Compare pgvector and hosted vector databases.</button>
          <button type="button">How do modern eval pipelines work?</button>
        </div>
      </section>
    </main>
  );
}

