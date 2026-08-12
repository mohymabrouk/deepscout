import ResearchComposer from "./components/research-composer";
import AuthPanel from "./components/auth-panel";
import SiteHeader from "./components/site-header";

export default function HomePage() {
  return (
    <main className="shell">
      <SiteHeader />
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
