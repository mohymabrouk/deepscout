export type StageEvent = {
  event: "stage" | "complete" | "error";
  stage?: string;
  message?: string;
  data?: Record<string, unknown>;
};

export type Source = {
  citation_id: number;
  title: string;
  url: string;
  domain: string;
  retrieved_at: string;
};

export type Paragraph = { text: string; citations: number[] };
export type Report = {
  title: string;
  executive_summary: string;
  sections: { heading: string; paragraphs: Paragraph[] }[];
  limitations: string[];
};
export type ResearchResult = {
  id: string;
  status: string;
  report?: Report;
  sources: Source[];
  usage?: { input_tokens: number; output_tokens: number; llm_calls: number };
  error_code?: string;
};

export const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function startResearch(question: string, idempotencyKey: string) {
  const response = await fetch(`${apiBase}/v1/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({ question, mode: "standard" }),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error?.message || "Research could not be started.");
  return payload as { run_id: string; status: string; events_url: string };
}

export async function getResearch(runId: string): Promise<ResearchResult> {
  const response = await fetch(`${apiBase}/v1/research/${runId}`, { cache: "no-store" });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error?.message || "Research run not found.");
  return payload;
}

export function subscribeToEvents(runId: string, onEvent: (event: StageEvent) => void) {
  const source = new EventSource(`${apiBase}/v1/research/${runId}/events`);
  const eventTypes: StageEvent["event"][] = ["stage", "complete", "error"];
  eventTypes.forEach((type) => {
    source.addEventListener(type, (event) => {
      onEvent({ ...(JSON.parse((event as MessageEvent).data) as StageEvent), event: type });
    });
  });
  return () => source.close();
}
