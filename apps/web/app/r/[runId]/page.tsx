"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getResearch, ResearchResult, StageEvent, subscribeToEvents } from "../../../lib/api";
import ReportView from "../../components/report-view";

const stages = [["planning", "Planning search"], ["searching", "Searching sources"], ["fetching", "Reading sources"], ["selecting", "Selecting evidence"], ["synthesizing", "Writing report"], ["verifying", "Verifying citations"]] as const;

export default function RunPage({ params }: { params: { runId: string } }) {
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [stage, setStage] = useState("planning");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getResearch(params.runId).then((value) => { if (active) { setResult(value); if (value.status !== "pending") setStage(value.status); if (value.status === "failed" || value.status === "limited") setError(value.error_code || "Research run failed."); } }).catch((cause) => active && setError(cause instanceof Error ? cause.message : "Run not found."));
    const unsubscribe = subscribeToEvents(params.runId, (event: StageEvent) => {
      if (event.stage) setStage(event.stage);
      if (event.event === "error") setError(String(event.data?.message || "Research run failed."));
      if (event.event === "complete") getResearch(params.runId).then((value) => active && setResult(value));
    });
    return () => { active = false; unsubscribe(); };
  }, [params.runId]);

  if (error && (result?.status === "failed" || result?.status === "limited" || !result)) return <main className="shell"><header className="header"><Link className="wordmark" href="/">DeepScout</Link></header><div className="state"><h1>{result?.status === "limited" ? "Research limit reached" : "Research run failed"}</h1><p className="error">{error}</p><Link className="primary link-button" href="/">Try again</Link></div></main>;
  if (result?.status === "completed" && result.report) return <main className="shell"><header className="header"><Link className="wordmark" href="/">DeepScout</Link><Link className="nav" href="/">New research</Link></header><ReportView report={result.report} sources={result.sources} /></main>;
  const currentIndex = stages.findIndex(([key]) => key === stage);
  return <main className="shell"><header className="header"><Link className="wordmark" href="/">DeepScout</Link></header><section className="state" aria-live="polite"><div className="eyebrow">Researching</div><h1>Reading the evidence.</h1><div className="progress">{stages.map(([key, label], index) => <div className={key === stage ? "progress-row current" : index < currentIndex ? "progress-row complete" : "progress-row"} key={key}><span aria-hidden="true">{index < currentIndex ? "✓" : key === stage ? "●" : "○"}</span>{label}</div>)}</div></section></main>;
}
