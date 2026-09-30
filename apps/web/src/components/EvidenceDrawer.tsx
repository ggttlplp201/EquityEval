"use client";

import { useEffect, useRef } from "react";
import type { EvidenceDetail, EvidenceSource } from "@/features/sectors/types";

export default function EvidenceDrawer({ detail, onClose, eyebrow = "FROZEN SNAPSHOT · FICTIONAL" }: { detail: EvidenceDetail | undefined; onClose: () => void; eyebrow?: string }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (detail && !dialog.current?.open) dialog.current?.showModal();
    if (!detail && dialog.current?.open) dialog.current.close();
  }, [detail]);
  return <dialog ref={dialog} className="source-drawer" onCancel={(event) => {
    // State owns closure; a queued native close event cannot clear the next inspection.
    event.preventDefault();
    onClose();
  }} onClick={(event) => {
    if (event.target !== event.currentTarget) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onClose();
  }} aria-labelledby="source-title">
    {detail ? <><div className="drawer-heading"><span className="eyebrow">{eyebrow}</span><button className="icon-button" onClick={onClose} aria-label="Close source details">×</button></div><h2 id="source-title">{detail.title}</h2><p className="muted">{detail.subtitle}</p>
      {detail.sections.map((section) => <section key={section.heading} className="source-section"><h3>{section.heading}</h3><dl>{section.rows.map((row, index) => <div key={`${row.label}-${index}`}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}</dl></section>)}
      <SourceList title="Source chain" sources={detail.sources} />
      {detail.reviewContext?.length ? <SourceList title="Review context (not PIT-selected)" sources={detail.reviewContext} /> : null}</> : null}
  </dialog>;
}

function SourceList({ title, sources }: { title: string; sources: EvidenceSource[] }) {
  return <section className="source-section" aria-label={title}><h3>{title}</h3>{sources.length ? sources.map((source, index) => <div className="source-item" key={`${source.label}-${index}`}><strong>{source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.label} ↗</a> : source.label}</strong>{source.accession ? <p>Accession · {source.accession}</p> : null}<p>Captured · {source.capturedAt}</p><p>Transform · {source.transform}</p><p>Usage · {source.licence}</p></div>) : <p>N/A</p>}</section>;
}
