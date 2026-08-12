"use client";

import { Report, Source } from "../../lib/api";

export default function ReportView({ report, sources }: { report: Report; sources: Source[] }) {
  const sourceById = new Map(sources.map((source) => [source.citation_id, source]));
  return (
    <div className="result-grid">
      <article className="report"><div className="eyebrow">Research brief</div><h1>{report.title}</h1><p className="summary">{report.executive_summary}</p>
        {report.sections.map((section) => <section key={section.heading} className="report-section"><h2>{section.heading}</h2>{section.paragraphs.map((paragraph, index) => <p key={`${section.heading}-${index}`}>{paragraph.text}{" "}{paragraph.citations.map((citation) => sourceById.has(citation) ? <a className="citation" href={`#source-${citation}`} key={citation} aria-label={`Source ${citation}`}>[{citation}]</a> : null)}</p>)}</section>)}
        {report.limitations.length > 0 && <section className="limitations"><h2>Limitations</h2><ul>{report.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>}
      </article>
      <aside className="sources" aria-label="Sources"><h2>Sources</h2>{sources.map((source) => <a className="source-card" id={`source-${source.citation_id}`} href={source.url} target="_blank" rel="noopener noreferrer" key={source.citation_id}><span className="source-number">{source.citation_id}</span><span><strong>{source.title}</strong><small>{source.domain}</small></span></a>)}</aside>
    </div>
  );
}

