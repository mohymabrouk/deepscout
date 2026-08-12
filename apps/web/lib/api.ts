export type StageEvent = {
  event: "stage" | "complete" | "error";
  stage?: string;
  message?: string;
  data?: Record<string, unknown>;
};

export type StageKey = "planning" | "searching" | "fetching" | "selecting" | "synthesizing" | "verifying";

export type Source = {
  citation_id: number;
  title: string;
  url: string;
  domain: string;
  retrieved_at: string;
  quality?: {
    score: number;
    label: "high" | "medium" | "low";
    reasons: string[];
  };
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
  question?: string;
  report?: Report;
  sources: Source[];
  usage?: { input_tokens: number; output_tokens: number; llm_calls: number };
  error_code?: string;
};

export const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

function headers(accessToken?: string | null): Record<string, string> {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
}

async function responsePayload(response: Response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error?.message || "The API request failed.");
  return payload;
}

export async function startResearch(question: string, idempotencyKey: string, accessToken?: string | null) {
  const response = await fetch(`${apiBase}/v1/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey, ...headers(accessToken) },
    body: JSON.stringify({ question, mode: "standard" }),
  });
  const payload = await responsePayload(response);
  return payload as { run_id: string; status: string; events_url: string };
}

export async function getResearch(runId: string, accessToken?: string | null): Promise<ResearchResult> {
  const response = await fetch(`${apiBase}/v1/research/${runId}`, {
    cache: "no-store",
    headers: headers(accessToken),
  });
  return responsePayload(response) as Promise<ResearchResult>;
}

export function subscribeToEvents(runId: string, accessToken: string | null, onEvent: (event: StageEvent) => void, onConnection?: (state: "connecting" | "open" | "reconnecting") => void) {
  const controller = new AbortController();
  let stopped = false;
  onConnection?.("connecting");
  const dispatch = (chunk: string) => {
    let eventType: StageEvent["event"] = "stage";
    let data = "";
    for (const line of chunk.split("\n")) {
      if (line.startsWith("event: ")) eventType = line.slice(7) as StageEvent["event"];
      if (line.startsWith("data: ")) data += line.slice(6);
    }
    if (!data || !["stage", "complete", "error"].includes(eventType)) return;
    onEvent({ ...(JSON.parse(data) as StageEvent), event: eventType });
  };
  const run = async () => {
    while (!stopped) {
      try {
        const response = await fetch(`${apiBase}/v1/research/${runId}/events`, {
          headers: headers(accessToken),
          signal: controller.signal,
        });
        if (!response.ok || !response.body) throw new Error("Live updates unavailable.");
        onConnection?.("open");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (!stopped) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const chunks = buffer.split("\n\n");
          buffer = chunks.pop() || "";
          chunks.forEach(dispatch);
        }
        if (buffer) dispatch(buffer);
        return;
      } catch {
        if (stopped) return;
        onConnection?.("reconnecting");
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }
  };
  void run();
  return () => { stopped = true; controller.abort(); };
}

export type RunSummary = {
  id: string;
  status: string;
  question: string;
  title?: string;
  source_count: number;
  created_at: string;
  completed_at?: string;
};

export async function getRuns(accessToken: string, limit = 20, cursor?: string | null) {
  const query = new URLSearchParams({ limit: String(limit) });
  if (cursor) query.set("cursor", cursor);
  const response = await fetch(`${apiBase}/v1/runs?${query.toString()}`, {
    cache: "no-store",
    headers: headers(accessToken),
  });
  return responsePayload(response) as Promise<{ items: RunSummary[]; next_cursor?: string }>;
}

export async function deleteRun(runId: string, accessToken: string) {
  const response = await fetch(`${apiBase}/v1/runs/${runId}`, {
    method: "DELETE",
    headers: headers(accessToken),
  });
  await responsePayload(response);
}
