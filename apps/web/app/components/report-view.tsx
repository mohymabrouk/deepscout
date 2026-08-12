"use client";

import { useState } from "react";
import { Report, Source } from "../../lib/api";

export default function ReportView({ report, sources }: { report: Report; sources: Source[] }) {
  const [highlightedSource, setHighlightedSource] = useState<number | null>(null);
  const sourceById = new Map(sources.map((source) => [source.citation_id, source]));

  function focusSource(citation: number) {
    setHighlightedSource(citation);
    document.getElementById(`source-${citation}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => setHighlightedSource(null), 2200);
  }

  return (
    <div className="result-grid">
      <article className="report">
        <div className="eyebrow">Research brief</div>
        <h1>{report.title}</h1>
        <p className="summary">{report.executive_summary}</p>
        {report.sections.map((section) => (
          <section key={section.heading} className="report-section">
            <h2>{section.heading}</h2>
            {section.paragraphs.map((paragraph, index) => (
              <p key={`${section.heading}-${index}`}>
                {paragraph.text}{" "}
                {paragraph.citations.map((citation) => {
                  const source = sourceById.get(citation);
                  if (!source) return null;
                  return <button className="citation" type="button" key={citation} title={`${source.title} · ${source.domain}`} onClick={() => focusSource(citation)}>[{citation}]</button>;
                })}
              </p>
            ))}
          </section>
        ))}
        {report.limitations.length > 0 && <section className="limitations"><h2>Limitations</h2><ul>{report.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>}
      </article>
      <details className="sources-panel" open>
        <summary>Sources <span>{sources.length}</span></summary>
        <aside className="sources" aria-label="Sources">
          {sources.map((source) => <a className={`source-card${highlightedSource === source.citation_id ? " highlighted" : ""}`} id={`source-${source.citation_id}`} href={source.url} target="_blank" rel="noopener noreferrer" key={source.citation_id}>
            <span className="source-number">{source.citation_id}</span>
            <span><strong>{source.title}</strong><small>{source.domain}</small></span>
          </a>)}
        </aside>
      </details>
    </div>
  );
}
