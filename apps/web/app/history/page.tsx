"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AuthPanel from "../components/auth-panel";
import { deleteRun, getRuns, RunSummary } from "../../lib/api";
import { getSupabaseBrowserClient } from "../../lib/supabase";

export default function HistoryPage() {
  const client = getSupabaseBrowserClient();
  const [token, setToken] = useState<string | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(() => Boolean(client));
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
        if (active) setRuns(result.items);
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

  return (
    <main className="shell">
      <header className="header"><Link className="wordmark" href="/">DeepScout</Link><nav className="nav"><Link href="/">New research</Link><Link href="/about">About</Link></nav></header>
      <section className="history-page">
        <div className="eyebrow">Private history</div>
        <h1>Return to your research.</h1>
        <p className="lede">Only runs owned by your signed-in account appear here. Delete a run when you no longer need it.</p>
        {!token && <AuthPanel />}
        {loading && <p className="auth-note">Loading history…</p>}
        {error && <p className="error" role="alert">{error}</p>}
        {token && !loading && runs.length === 0 && <p className="empty-state">No saved runs yet. Start a research brief to see it here.</p>}
        {token && runs.length > 0 && <div className="history-list">{runs.map((run) => <article className="history-row" key={run.id}><Link href={`/r/${run.id}`}><span className="history-status">{run.status}</span><h2>{run.title || run.question}</h2><p>{run.question}</p><small>{new Date(run.created_at).toLocaleString()} · {run.source_count} sources</small></Link><button className="quiet-button" type="button" onClick={() => remove(run)}>Delete</button></article>)}</div>}
      </section>
    </main>
  );
}
