"use client";

import { FormEvent, KeyboardEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { startResearch, uploadDocument } from "../../lib/api";
import { getAccessToken } from "../../lib/supabase";

const examples = [
  "Compare pgvector and hosted vector databases for a small SaaS.",
  "How do modern LLM evaluation pipelines work?",
];

export default function ResearchComposer() {
  const [question, setQuestion] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [document, setDocument] = useState<File | null>(null);
  const router = useRouter();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function resizeTextarea() {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 224)}px`;
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    if (submitting) return;
    setError("");
    setSubmitting(true);
    try {
      const accessToken = await getAccessToken();
      const uploaded = document ? await uploadDocument(document, accessToken) : null;
      const result = await startResearch(question, crypto.randomUUID(), accessToken, uploaded ? [uploaded.id] : []);
      router.push(`/r/${result.run_id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Research could not be started.");
      setSubmitting(false);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") submit();
    if (event.key === "Escape") setQuestion("");
  }

  return (
    <>
      <form className="composer" onSubmit={submit} aria-label="Research question">
        <label className="sr-only" htmlFor="research-question">Research question</label>
        <textarea id="research-question" ref={textareaRef} aria-describedby="research-question-hint" aria-keyshortcuts="Control+Enter Meta+Enter" value={question} onChange={(event) => { setQuestion(event.target.value); resizeTextarea(); }} onKeyDown={onKeyDown} maxLength={1500} placeholder="What would you like to investigate?" required minLength={10} disabled={submitting} />
        <div className="composer-footer"><span className="hint" id="research-question-hint">Cmd/Ctrl + Enter to research · Esc to clear</span><span className="character-count" aria-live="polite">{question.length > 1300 ? `${question.length}/1500` : ""}</span><button className="primary" type="submit" disabled={submitting}>{submitting ? "Starting…" : "Research"}</button></div>
      </form>
      <label className="document-picker">Attach a PDF (optional)<input type="file" accept="application/pdf,.pdf" onChange={(event) => setDocument(event.target.files?.[0] ?? null)} disabled={submitting} /><span>{document ? document.name : "No PDF selected"}</span></label>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="examples" aria-label="Example questions"><span>Try:</span>{examples.map((example) => <button key={example} type="button" onClick={() => { setQuestion(example); requestAnimationFrame(resizeTextarea); }}>{example}</button>)}</div>
    </>
  );
}
