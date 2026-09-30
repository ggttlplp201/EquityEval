"use client";

import Link from "next/link";
import { useState } from "react";
import type { PublicMetric } from "@equity/schema/types/fundamentals";
import WorkbenchShell from "@/components/WorkbenchShell";
import EvidenceDrawer from "@/components/EvidenceDrawer";
import type { EvidenceDetail } from "@/features/sectors/types";
import EvidenceValue from "@/features/valuation/EvidenceValue";
import { exact, number, words } from "@/features/valuation/presentation";
import { metrics, metricDisplay, savedNotes, sections, statuses, chartLabels } from "./presentation";
import type { ExampleChoice, SavedFundamentals } from "./types";
import styles from "./fundamentals.module.css";

export default function FundamentalsWorkspace({ saved, examples, label }: {
  saved: SavedFundamentals; examples: ExampleChoice[]; label: string;
}) {
  const [detail, setDetail] = useState<EvidenceDetail>();
  const [pending, setPending] = useState(false);
  const [historyMetric, setHistoryMetric] = useState(saved.payload.metrics.find((m) => m.metric_id === "operating_margin")?.metric_id ?? saved.payload.metrics[0].metric_id);
  const payload = saved.payload;
  const selector = payload.selector;
  const choice = examples.find((e) => e.id === saved.example)!;
  const history = payload.history.find((h) => h.metric_id === historyMetric);
  const metric = payload.metrics.find((m) => m.metric_id === historyMetric)!;
  const positions = saved.chart_positions[historyMetric];
  function navigate(example: string, date: string, years: string) {
    setPending(true);
    window.location.assign(`/development/company/ratios?${new URLSearchParams({ example, date, years })}`);
  }
  function inspect(title: string, value: unknown, indices?: readonly number[], historical = false) {
    const evidence = historical ? [] : indices ? payload.evidence.filter((e) => indices.includes(e.input_index)) : payload.evidence;
    setDetail({ title, subtitle: `${label} · ${historical ? "saved historical band and snapshot references" : "offline S6a example"} · exact saved decimal evidence`,
      sections: [
        { heading: "Selected evidence", rows: [{ label: title, value: exact(value) }] },
        { heading: "Snapshot identity", rows: [{ label: "Snapshot", value: saved.snapshot_id }, { label: "Input snapshot", value: saved.input_snapshot_id }, { label: "Payload hash", value: saved.payload_hash }, { label: "Dependency hash", value: payload.dependency_hash }, { label: "Comparison policy hash", value: payload.comparison_policy_hash }] },
        { heading: "Selection and policies", rows: [{ label: "Saved selector", value: exact(selector) }] },
        { heading: historical ? "Historical snapshot references" : "Source evidence", rows: historical ? [{ label: "Saved history", value: exact(history) }, { label: "Historical sample operands", value: "N/A" }] : evidence.map((e) => ({ label: `${e.input_index} · ${words(e.concept)}`, value: exact(e) })) },
      ], sources: evidence.map((e) => ({ label: e.source_tag ?? words(e.concept), url: e.source_url ?? undefined, accession: e.accession ?? undefined,
        capturedAt: e.retrieved_at.join(" · ") || "N/A", transform: `${e.normalizer_revision} · ${e.normalization_operation ?? "N/A"} · selection ${e.selection_hash}`, licence: "Fictional presentation source; no company observations" })),
    });
  }
  const value = (title: string, raw: string | number | null, evidence: unknown, display?: string) => <EvidenceValue title={title} value={raw} display={display} evidence={evidence} onInspect={inspect} />;
  const historyValue = (title: string, raw: string | number | null, display?: string) => <EvidenceValue title={title} value={raw} display={display} evidence={history} onInspect={(title, evidence) => inspect(title, evidence, undefined, true)} />;
  function metricCards(ids: string[]) {
    const rows = ids.flatMap((id) => payload.metrics.filter((m) => m.metric_id === id));
    return rows.length ? <div className={styles.cards}>{rows.map((m: PublicMetric) => <article key={m.metric_id} data-metric={m.metric_id} data-status={m.status} className={styles.card}>
      <h3>{metrics[m.metric_id].label}</h3><p>{metrics[m.metric_id].definition}</p>
      <div className={styles.metricValue}><EvidenceValue title={metrics[m.metric_id].label} value={m.value} display={metricDisplay(m)} evidence={m} onInspect={(title, evidence) => inspect(title, evidence, m.input_indices)} />{m.unit === "USD" ? <span> USD</span> : null}</div>
      <span className={styles.badge}>{statuses[m.status]}</span><p className={styles.reasons}>{m.reasons.map(words).join(" · ")}</p>
    </article>)}</div> : <p>N/A</p>;
  }
  return <WorkbenchShell active="fundamentals" fictional><main id="main-content" tabIndex={-1} className={styles.page}>
    <header className={styles.heading}><div><p className="eyebrow">COMPANY / FICTIONAL S6a EXAMPLE</p><h1>Fundamentals</h1><p>{label}</p></div><Link href="/help#fundamentals">Five-minute guide ↗</Link></header>
    <p className={styles.separate}>Separate fictional example from the Company overview.</p>
    <section className={styles.context} aria-label="Saved selection">
      <label>Example<select aria-label="Fundamentals example" disabled={pending} value={saved.example} onChange={(e) => { const next = examples.find((x) => x.id === e.target.value)!; navigate(next.id, next.dates.at(-1)!, String(saved.years)); }}>{examples.map((e) => <option key={e.id} value={e.id}>{e.label}</option>)}</select></label>
      <label>Evaluation date<select aria-label="Evaluation date" disabled={pending} value={selector.as_of} onChange={(e) => navigate(saved.example, e.target.value, String(saved.years))}>{choice.dates.map((date) => <option key={date}>{date}</option>)}</select></label>
      <div><span>Basis / currency</span><strong>{words(selector.period_basis)} · {words(selector.reporting_basis)} · {selector.currency}</strong></div>
      <div><span>Financial period</span><strong>{selector.period_start ? `${selector.period_start} – ` : ""}{selector.period_end}</strong></div>
      <div><span>Filed cutoff / captured by</span><strong>{selector.filed_cutoff ?? "N/A"} / {selector.captured_before}</strong></div>
      <div><span>History mode</span><strong>{words(selector.history_mode)}</strong></div>
      <div className={styles.identity}><span>Fictional snapshot</span><button className="text-button" onClick={() => inspect("Snapshot identity", saved.snapshot_id)}>{saved.snapshot_id}</button></div>
    </section>
    <p role="status">{pending ? "Loading saved selection…" : `${choice.label} · ${selector.as_of} · ${saved.years}-year history`}</p>
    <section className={styles.panel} aria-labelledby="coverage-title"><h2 id="coverage-title">Coverage</h2>
      <div className={styles.coverage}><div><span>Covered / applicable</span><strong>{value("Covered count", payload.coverage.covered_count, payload.coverage)} / {value("Applicable count", payload.coverage.applicable_count, payload.coverage)}</strong></div><div><span>Coverage</span><strong>{value("Coverage fraction", payload.coverage.fraction, payload.coverage, number(payload.coverage.fraction, true))}</strong></div><div><span>Unresolved applicability</span><strong>{value("Unresolved count", payload.coverage.unresolved_count, payload.coverage)}</strong></div></div>
      <div className={styles.statuses}>{Object.entries(statuses).map(([status, title]) => <div key={status} data-coverage-status={status}><span>{title}</span>{value(`${title} count`, payload.coverage.counts[status] ?? null, payload.coverage)}</div>)}</div>
    </section>
    {savedNotes(payload).length ? <section className={styles.panel} aria-labelledby="notes-title"><h2 id="notes-title">Saved review notes</h2><ul>{savedNotes(payload).map((item) => <li key={item.topic}><button className="text-button" onClick={() => inspect("Saved review note", item)}>{item.text}</button></li>)}</ul></section> : null}
    {sections.slice(0, 5).map((section, index) => <section className={styles.panel} key={section.title} data-fundamentals-section={section.title}><h2><span className={styles.index}>{index + 1}</span>{section.title}</h2>{metricCards(section.ids)}</section>)}
    <details className={styles.panel}><summary>Returns on capital</summary>{metricCards(sections[5].ids)}</details>
    <section className={styles.panel} aria-labelledby="history-title"><div className={styles.heading}><h2 id="history-title">Own-history comparison</h2><div className={styles.controls}>
      <label>Metric<select aria-label="History metric" value={historyMetric} onChange={(e) => setHistoryMetric(e.target.value)}>{payload.metrics.map((m) => <option key={m.metric_id} value={m.metric_id}>{metrics[m.metric_id].label}</option>)}</select></label>
      <label>Window<select aria-label="History window" disabled={pending} value={saved.years} onChange={(e) => navigate(saved.example, selector.as_of, e.target.value)}>{[3, 5, 10].map((years) => <option key={years} value={years}>{years} years</option>)}</select></label>
    </div></div>{history ? <>
      <p data-history-window>Requested {history.years} years · ({history.window_start}, {history.window_end}]</p>
      <p data-history-coverage>Eligible {historyValue("Eligible history count", history.eligible_snapshot_ids.length)} · Excluded {historyValue("Excluded history count", history.excluded.length)} · Minimum {historyValue("History minimum", history.minimum_samples)} · Missing quarter ends {historyValue("Missing quarter count", history.missing_quarter_ends.length)}</p>
      <p data-history-reasons>{history.reasons.map(words).join(" · ") || "Saved comparison available"}</p>
      {positions && history.p25 !== null && history.p50 !== null && history.p75 !== null ? <figure className={styles.chart}><svg viewBox="0 0 600 110" role="img" aria-label={`Saved ${metrics[historyMetric].label} history: P25 ${metricDisplay({ ...metric, value: history.p25 })}, median ${metricDisplay({ ...metric, value: history.p50 })}, P75 ${metricDisplay({ ...metric, value: history.p75 })}`}>
        <line x1={`${positions[0]}%`} x2={`${positions[2]}%`} y1="42" y2="42" stroke="currentColor" strokeWidth="4" />
        {chartLabels(positions).map(({ x, label }) => <g key={x}><line x1={`${x}%`} x2={`${x}%`} y1="30" y2="54" stroke="currentColor" strokeWidth="3" /><text x={`${x}%`} y="80" textAnchor="middle">{label}</text></g>)}
      </svg><figcaption>Saved middle 50% of eligible observations · {history.relation ? `${history.relation} own-history band` : "N/A"}</figcaption></figure> : <p className={styles.unavailable} data-history-unavailable>History chart · N/A</p>}
      <div className={styles.tableWrap} tabIndex={0} role="region" aria-label="Saved history values"><table><caption>Rounded display · select for exact saved evidence</caption><thead><tr><th>P25</th><th>Median · P50</th><th>P75</th><th>Comparison</th></tr></thead><tbody><tr>{(["p25", "p50", "p75"] as const).map((key) => <td key={key}>{historyValue(key.toUpperCase(), history[key], history[key] === null ? "N/A" : metricDisplay({ ...metric, value: history[key] }))}</td>)}<td>{history.relation ?? "N/A"}</td></tr></tbody></table></div>
      <details className={styles.historyDetails}><summary>Coverage dates and exclusions</summary><h3>Missing quarter ends</h3><p data-missing-quarters>{history.missing_quarter_ends.join(" · ") || "None"}</p><h3>Excluded snapshots</h3>{history.excluded.length ? <ul>{history.excluded.map(([id, reasons]) => <li key={id}><button className="text-button" onClick={() => inspect("Excluded history snapshot", { snapshot_id: id, reasons, history }, undefined, true)}>{id}</button> · {reasons.map(words).join(" · ")}</li>)}</ul> : <p>None</p>}<h3>Eligible snapshot IDs</h3><p>{history.eligible_snapshot_ids.join(" · ") || "None"}</p></details>
    </> : <p>N/A</p>}</section>
    <footer className={styles.footer}><Link href="/development/company" prefetch={false}>Company overview example</Link><Link href="/development/valuation" prefetch={false}>Reverse DCF example</Link><Link href="/help#fundamentals" prefetch={false}>Fundamentals guide</Link><button className="text-button" onClick={() => inspect("Complete saved payload", payload)}>Inspect full snapshot evidence</button></footer>
  </main><EvidenceDrawer detail={detail} onClose={() => setDetail(undefined)} /></WorkbenchShell>;
}
