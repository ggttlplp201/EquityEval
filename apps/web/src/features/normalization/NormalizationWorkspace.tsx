"use client";

import Link from "next/link";
import { useState } from "react";
import WorkbenchShell from "@/components/WorkbenchShell";
import EvidenceDrawer from "@/components/EvidenceDrawer";
import { number } from "@/features/valuation/presentation";
import type { NormalizationSnapshot } from "./types";
import styles from "./normalization.module.css";

export default function NormalizationWorkspace({ data }: { data: NormalizationSnapshot }) {
  const [mode, setMode] = useState("as_filed");
  const [detail, setDetail] = useState<string | null>(null);
  const view = data.views[mode];
  return <WorkbenchShell active="pilot">
    <main id="main-content" tabIndex={-1} className={styles.page} data-normalization-kind={data.kind}>
      <Link href="/development/pilot/pipeline" className={styles.back}>← Application pipeline</Link>
      <header className={styles.header}>
        <div><p className="eyebrow">CRCL / REAL SOURCE DATA</p><h1>Normalized financials<span>.</span></h1><p>Filed-date reconstruction</p></div>
        <button className={styles.stamp} onClick={() => setDetail("publication")} aria-label="Inspect publication dates and evidence"><strong>{data.periodLabel}</strong><span>Captured {data.retrievalCutoff.slice(0, 10)}</span><span>Published {data.publishedAt.slice(0, 10)} ↗</span></button>
      </header>
      <section className={styles.stats} aria-label="Published batch counts">
        {[["Selected facts", data.factCount], ["Source captures", data.captureCount], ["Quality flags", data.flagCount]].map(([label, value]) => <button key={label} onClick={() => setDetail(label === "Quality flags" ? "eligibility" : "publication")}><span>{label}</span><strong>{value}</strong></button>)}
      </section>
      <div className={styles.controls}><label htmlFor="history-mode">History selection</label><select id="history-mode" value={mode} onChange={(event) => setMode(event.target.value)}>{Object.entries(data.views).map(([id, item]) => <option key={id} value={id}>{item.label}</option>)}</select></div>
      <section className={styles.facts} aria-label="Normalized annual figures" aria-live="polite">
        {view.facts.map((fact) => <article key={fact.id} data-normalized-concept={fact.id}><p className="eyebrow">CONSOLIDATED / USD</p><h2>{fact.label}</h2><button className={styles.amount} onClick={() => setDetail(fact.detailId)} aria-label={`Inspect ${fact.label}`}><strong>{fact.value === null ? "N/A" : `$${number(fact.value)}`}</strong><span aria-hidden="true">↗</span></button><p>{data.periodLabel} · {view.label}</p></article>)}
      </section>
      <section className={styles.next} aria-label="Analysis"><div><h2>Financial analysis</h2><span>N/A</span></div><Link href="/development/pilot/analysis">Inspect analysis readiness ↗</Link></section>
      <footer className={styles.footer}><button onClick={() => setDetail("publication")}>Publication &amp; source records ↗</button><Link href="/help#real-normalization">User guide ↗</Link></footer>
    </main>
    <EvidenceDrawer detail={detail ? data.details[detail] : undefined} onClose={() => setDetail(null)} eyebrow="REAL APPLICATION / CRCL" />
  </WorkbenchShell>;
}
