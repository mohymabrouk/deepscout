"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AuthPanel from "../components/auth-panel";
import SiteHeader from "../components/site-header";
import { deleteRun, getRuns, RunSummary } from "../../lib/api";
import { getSupabaseBrowserClient } from "../../lib/supabase";

export default function HistoryPage() {
  const client = getSupabaseBrowserClient();
  const [token, setToken] = useState<string | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(() => Boolean(client));
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!client) return;
    let active = true;
    const load = async (accessToken: string | null) => {
      setToken(accessToken);
      if (!accessToken) { setRuns([]); setLoading(false); return; }
      setLoading(true);
      setError("");
      try {
        const result = await getRuns(accessToken);
        if (active) { setRuns(result.items); setNextCursor(result.next_cursor ?? null); }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "History could not be loaded.");
      } finally { if (active) setLoading(false); }
    };
    client.auth.getSession().then(async ({ data }) => {
      const accessToken = data.session?.access_token ?? null;
      if (!active) return;
      await load(accessToken);
    });
    const { data: listener } = client.auth.onAuthStateChange((_event, session) => {
      void load(session?.access_token ?? null);
    });
    return () => { active = false; listener.subscription.unsubscribe(); };
  }, [client]);

  async function remove(run: RunSummary) {
    if (!token || !window.confirm("Delete this research run permanently?")) return;
    try {
      await deleteRun(run.id, token);
      setRuns((current) => current.filter((item) => item.id !== run.id));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Run could not be deleted."); }
  }

  async function loadMore() {
    if (!token || !nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const result = await getRuns(token, 20, nextCursor);
      setRuns((current) => [...current, ...result.items]);
      setNextCursor(result.next_cursor ?? null);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "More history could not be loaded."); }
    finally { setLoadingMore(false); }
  }

  return (
    <main className="shell">
      <SiteHeader active="history" />
      <section className="content-page history-page">
        <div className="page-intro history-intro">
          <div>
            <div className="eyebrow">Private history</div>
            <h1>Return to your research.</h1>
            <p className="lede">Your completed briefs, source lists, and report details in one place. History is available to signed-in accounts only.</p>
          </div>
          <Link className="primary link-button intro-action" href="/">New research <span aria-hidden="true">→</span></Link>
        </div>
        <div className="history-explainer">
          <div><span className="note-label">What is saved</span><p>Completed runs, their report title, status, source count, and the report itself.</p></div>
          <div><span className="note-label">Who can see it</span><p>Only the signed-in account that created the run. Anonymous runs are not listed here.</p></div>
          <div><span className="note-label">Your control</span><p>Open a report again or permanently delete it from this page.</p></div>
        </div>
        {!token && <AuthPanel />}
        {loading && <div className="history-skeleton" aria-label="Loading history"><span /><span /><span /></div>}
        {error && <p className="error" role="alert">{error}</p>}
        {token && !loading && runs.length === 0 && <div className="empty-state"><span className="empty-mark" aria-hidden="true">+</span><div><h2>No saved research yet.</h2><p>Start a brief and it will appear here once you are signed in.</p><Link className="quiet-link" href="/">Start a research brief <span aria-hidden="true">→</span></Link></div></div>}
        {token && runs.length > 0 && <><div className="history-list" aria-label="Saved research runs">{runs.map((run) => <article className="history-row" key={run.id}><Link className="history-link" href={`/r/${run.id}`}><div className="history-row-top"><span className={`history-status status-${run.status}`}>{run.status}</span><small>{new Date(run.created_at).toLocaleString()}</small></div><h2>{run.title || run.question || "Research run"}</h2><p>{run.question || "Question text was not stored."}</p><div className="history-meta"><span>{run.source_count} {run.source_count === 1 ? "source" : "sources"}</span><span className="history-open">Open report <span aria-hidden="true">→</span></span></div></Link><button className="quiet-button" type="button" onClick={() => remove(run)}>Delete</button></article>)}</div>{nextCursor && <button className="quiet-button load-more" type="button" onClick={loadMore} disabled={loadingMore}>{loadingMore ? "Loading…" : "Load more"}</button>}</>}
      </section>
    </main>
  );
}
