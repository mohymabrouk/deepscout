import Link from "next/link";

export default function AboutPage() {
  return (
    <main className="shell">
      <header className="header"><Link className="wordmark" href="/">DeepScout</Link></header>
      <article className="hero">
        <div className="eyebrow">Methodology</div>
        <h1>Small, bounded research runs.</h1>
        <p className="lede">DeepScout plans a few focused searches, reads a bounded set of public pages, and writes only from selected evidence. Sources are shown so you can verify the result.</p>
      </article>
    </main>
  );
}
