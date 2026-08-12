"use client";

import { FormEvent, KeyboardEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { startResearch } from "../../lib/api";

const examples = [
  "Compare pgvector and hosted vector databases for a small SaaS.",
  "How do modern LLM evaluation pipelines work?",
];

export default function ResearchComposer() {
  const [question, setQuestion] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    if (submitting) return;
    setError("");
    setSubmitting(true);
    try {
      const result = await startResearch(question, crypto.randomUUID());
      router.push(`/r/${result.run_id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Research could not be started.");
      setSubmitting(false);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") submit();
  }

  return (
    <>
      <form className="composer" onSubmit={submit} aria-label="Research question">
        <textarea aria-label="Research question" value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={onKeyDown} maxLength={1500} placeholder="What would you like to investigate?" required minLength={10} disabled={submitting} />
        <div className="composer-footer"><span className="hint">Cmd/Ctrl + Enter to research</span><button className="primary" type="submit" disabled={submitting}>{submitting ? "Starting…" : "Research"}</button></div>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="examples" aria-label="Example questions"><span>Try:</span>{examples.map((example) => <button key={example} type="button" onClick={() => setQuestion(example)}>{example}</button>)}</div>
    </>
  );
}
