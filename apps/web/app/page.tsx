import Link from "next/link";
import ResearchComposer from "./components/research-composer";
import AuthPanel from "./components/auth-panel";

export default function HomePage() {
  return (
    <main className="shell">
      <header className="header">
        <Link className="wordmark" href="/">DeepScout</Link>
        <nav className="nav" aria-label="Primary navigation">
          <Link href="/history">History</Link>
          <Link href="/about">About</Link>
        </nav>
      </header>
      <section className="hero">
        <div className="eyebrow">Research with evidence</div>
        <h1>Ask a focused question. Get a brief you can inspect.</h1>
        <p className="lede">DeepScout searches, reads, and returns a concise source-backed answer.</p>
        <ResearchComposer />
        <div className="home-auth"><AuthPanel compact /></div>
      </section>
    </main>
  );
}
