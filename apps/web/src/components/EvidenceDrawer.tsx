"use client";

import { useEffect, useRef } from "react";
import type { EvidenceDetail } from "@/features/sectors/types";

export default function EvidenceDrawer({ detail, onClose }: { detail: EvidenceDetail | undefined; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (detail && !dialog.current?.open) dialog.current?.showModal();
    if (!detail && dialog.current?.open) dialog.current.close();
  }, [detail]);
  return <dialog ref={dialog} className="source-drawer" onClose={onClose} onClick={(event) => {
    if (event.target !== event.currentTarget) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onClose();
  }} aria-labelledby="source-title">
    {detail ? <><div className="drawer-heading"><span className="eyebrow">FROZEN SNAPSHOT · FICTIONAL</span><button className="icon-button" onClick={onClose} aria-label="Close source details">×</button></div><h2 id="source-title">{detail.title}</h2><p className="muted">{detail.subtitle}</p>
      {detail.sections.map((section) => <section key={section.heading} className="source-section"><h3>{section.heading}</h3><dl>{section.rows.map((row, index) => <div key={`${row.label}-${index}`}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}</dl></section>)}
      <section className="source-section"><h3>Source chain</h3>{detail.sources.map((source, index) => <div className="source-item" key={`${source.label}-${index}`}><strong>{source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.label} ↗</a> : source.label}</strong>{source.accession ? <p>Accession · {source.accession}</p> : null}<p>Captured · {source.capturedAt}</p><p>Transform · {source.transform}</p><p>Usage · {source.licence}</p></div>)}</section></> : null}
  </dialog>;
}
