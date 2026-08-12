"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { getResearch, ResearchResult, StageEvent, StageKey, subscribeToEvents } from "../../../lib/api";
import ReportView from "../../components/report-view";
import ShareButton from "../../components/share-button";
import StageProgress from "../../components/stage-progress";
import SiteHeader from "../../components/site-header";
import { getAccessToken } from "../../../lib/supabase";

export default function RunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = use(params);
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [stage, setStage] = useState<StageKey>("planning");
  const [stageData, setStageData] = useState<Record<string, unknown>>({});
  const [error, setError] = useState("");
  const [connectionState, setConnectionState] = useState<"connecting" | "open" | "reconnecting">("connecting");

  useEffect(() => {
    let active = true;
    let unsubscribe = () => {};
    getAccessToken().then((accessToken) => {
      if (!active) return;
      getResearch(runId, accessToken).then((value) => {
      if (!active) return;
      setResult(value);
      if (value.status !== "pending") setStage(value.status as StageKey);
      if (value.status === "failed" || value.status === "limited") setError(value.error_code || "Research run failed.");
      }).catch((cause) => active && setError(cause instanceof Error ? cause.message : "Run not found."));
      unsubscribe = subscribeToEvents(runId, accessToken, (event: StageEvent) => {
      if (event.stage) setStage(event.stage as StageKey);
      if (event.data) setStageData(event.data);
      if (event.event === "error") getResearch(runId, accessToken).then((value) => { if (active) { setResult(value); setError(value.error_code || "Research run failed."); } });
      if (event.event === "complete") getResearch(runId, accessToken).then((value) => active && setResult(value));
      }, setConnectionState);
    });
    return () => { active = false; unsubscribe(); };
  }, [runId]);

  if (error && (result?.status === "failed" || result?.status === "limited" || !result)) return <main className="shell"><SiteHeader /><div className="state"><h1>{result?.status === "limited" ? "Research limit reached" : "Research run failed"}</h1><p className="error">{error}</p><Link className="primary link-button" href="/">Try again</Link></div></main>;
  if (result?.status === "completed" && result.report) return <main className="shell"><SiteHeader actions={<><ShareButton /><Link className="nav-link" href="/">New research</Link></>} /><ReportView report={result.report} sources={result.sources} /></main>;
  return <main className="shell"><SiteHeader /><section className="state" aria-live="polite"><div className="eyebrow">Researching</div><h1>Reading the evidence.</h1><p className="progress-status">{connectionState === "reconnecting" ? "Live updates reconnecting…" : "Stage updates are live."}</p><StageProgress stage={stage} data={stageData} /><div className="loading-skeleton" aria-hidden="true"><span /><span /><span /></div></section></main>;
}
