"use client";

import { FormEvent, useEffect, useState } from "react";
import { getSupabaseBrowserClient } from "../../lib/supabase";

export default function AuthPanel({ compact = false }: { compact?: boolean }) {
  const client = getSupabaseBrowserClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [signedInEmail, setSignedInEmail] = useState<string | null>(null);
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!client) return;
    client.auth.getSession().then(({ data }) => setSignedInEmail(data.session?.user.email ?? null));
    const { data: listener } = client.auth.onAuthStateChange((_event, session) => {
      setSignedInEmail(session?.user.email ?? null);
    });
    return () => listener.subscription.unsubscribe();
  }, [client]);

  if (!client) {
    return compact ? null : <p className="auth-note">Configure Supabase Auth to enable accounts.</p>;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!client) return;
    const supabase = client;
    setBusy(true);
    setMessage("");
    const result = mode === "signin"
      ? await supabase.auth.signInWithPassword({ email, password })
      : await supabase.auth.signUp({ email, password });
    if (result.error) setMessage(result.error.message);
    else setMessage(mode === "signup" ? "Check your email to confirm your account." : "Signed in.");
    setBusy(false);
  }

  if (signedInEmail) {
    return (
      <div className={compact ? "auth-compact" : "auth-card"}>
        <span className="auth-email">{signedInEmail}</span>
        <button className="quiet-button" type="button" onClick={() => client.auth.signOut()}>Sign out</button>
      </div>
    );
  }

  return (
    <form className={compact ? "auth-compact auth-form" : "auth-card auth-form"} onSubmit={submit}>
      {!compact && <><div className="eyebrow">Your research history</div><h2>{mode === "signin" ? "Sign in" : "Create an account"}</h2></>}
      <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" /></label>
      <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={6} autoComplete={mode === "signin" ? "current-password" : "new-password"} /></label>
      <button className="primary" type="submit" disabled={busy}>{busy ? "Working…" : mode === "signin" ? "Sign in" : "Create account"}</button>
      <button className="text-button" type="button" onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setMessage(""); }}>{mode === "signin" ? "Need an account? Create one" : "Already have an account? Sign in"}</button>
      {message && <p className="auth-note" role="status">{message}</p>}
    </form>
  );
}
