"use client";

import { StageKey } from "../../lib/api";

const stages: { key: StageKey; label: string }[] = [
  { key: "planning", label: "Planning search" },
  { key: "searching", label: "Searching sources" },
  { key: "fetching", label: "Reading sources" },
  { key: "selecting", label: "Selecting evidence" },
  { key: "synthesizing", label: "Writing report" },
  { key: "verifying", label: "Verifying citations" },
];

export default function StageProgress({ stage, data }: { stage: string; data: Record<string, unknown> }) {
  const currentIndex = stages.findIndex((item) => item.key === stage);
  const safeIndex = currentIndex < 0 ? 0 : currentIndex;
  return (
    <div className="progress" role="list" aria-label="Research progress" aria-live="polite">
      {stages.map((item, index) => {
        const complete = index < safeIndex;
        const current = item.key === stage;
        const detail = item.key === "searching" && typeof data.sources_found === "number"
          ? `${data.sources_found} found`
          : item.key === "fetching" && typeof data.completed === "number" && typeof data.total === "number"
            ? `${data.completed} / ${data.total}`
            : "";
        return (
          <div className={`progress-row${current ? " current" : ""}${complete ? " complete" : ""}`} key={item.key} role="listitem" aria-current={current ? "step" : undefined}>
            <span className="progress-icon" aria-hidden="true">{complete ? "✓" : current ? "●" : "○"}</span>
            <span>{item.label}</span>
            {detail && <small>{detail}</small>}
          </div>
        );
      })}
    </div>
  );
}
