"use client";

import { useState } from "react";
import Link from "next/link";
import WorkbenchShell from "@/components/WorkbenchShell";
import EvidenceDrawer from "@/components/EvidenceDrawer";
import type { EvidenceDetail } from "@/features/sectors/types";
import EvidenceValue from "@/features/valuation/EvidenceValue";
import { exact, number } from "@/features/valuation/presentation";
import type { Basis, Choice, Family, SavedFinancials, StatementRow } from "./types";
import styles from "./financials.module.css";

const titles: Record<Family, string> = { income: "Income statement", balance_sheet: "Balance sheet", cash_flow: "Cash flow" };
export default function FinancialsWorkspace({ saved, choices }: { saved: SavedFinancials; choices: Choice[] }) {
  const [detail, setDetail] = useState<EvidenceDetail>();
  const [pending, setPending] = useState(false);
  function navigate(basis: Basis, edition: string) {
    setPending(true);
    window.location.assign(`/development/company/financials?${new URLSearchParams({ basis, edition })}`);
  }
  function inspect(title: string, row?: StatementRow, statement?: SavedFinancials["statements"][number]) {
    const identity = Object.fromEntries(Object.entries(saved).filter(([key]) => key !== "statements"));
    const evidence = row?.evidence ?? statement?.rows[0]?.evidence;
    setDetail({
      title, subtitle: `${saved.company} · ${saved.label}`,
      sections: [
        { heading: "Snapshot identity", rows: [{ label: "Saved selection", value: exact(identity) }] },
        { heading: "Exact source evidence", rows: [{ label: row?.label ?? (statement ? "Saved statement coverage and row evidence" : "Saved statements"), value: exact(row ?? statement ?? saved.statements) }] },
      ],
      sources: evidence ? [{ label: evidence.fixture_source, accession: evidence.accession ?? undefined,
        capturedAt: evidence.retrieved_at, transform: exact(evidence.transform), licence: "Fictional fixture" }] : [],
    });
  }
  return <WorkbenchShell active="financials" fictional><main id="main-content" tabIndex={-1} className={styles.page} data-snapshot={saved.snapshot_id}>
    <header className={styles.heading}><div><p className="eyebrow">COMPANY / SAVED STATEMENTS</p><h1>Financials</h1><p>{saved.company}</p></div><Link href="/help#financials">Financials guide ↗</Link></header>
    <section className={styles.context} aria-label="Saved financial statement selection">
      <div className={styles.basis} role="group" aria-label="Reporting period">
        {(["annual", "quarter"] as const).map((basis) => <button key={basis} type="button" aria-pressed={saved.basis === basis} disabled={pending || !choices.some((choice) => choice.basis === basis)} onClick={() => navigate(basis, basis === "annual" ? "annual_original" : "quarter")}>{basis === "annual" ? "Annual" : "Quarterly"}</button>)}
        <button type="button" disabled>TTM · N/A</button>
      </div>
      <label>Saved edition<select aria-label="Saved edition" value={saved.edition} disabled={pending} onChange={(event) => navigate(saved.basis, event.target.value)}>{choices.filter((choice) => choice.basis === saved.basis).map((choice) => <option key={choice.edition} value={choice.edition}>{choice.label}</option>)}</select></label>
      <dl><div><dt>Units / scope</dt><dd>{saved.currency} · units · {saved.scope}</dd></div><div><dt>Filed / known on</dt><dd>{saved.filed_on} / {saved.known_on}</dd></div><div><dt>Retrieved</dt><dd>{saved.retrieved_at}</dd></div><div><dt>History mode</dt><dd>{saved.history_mode === "original_as_filed" ? "Original as filed" : "Latest reported · saved revision"}</dd></div></dl>
      <button className="text-button" onClick={() => inspect("Snapshot identity")}>{saved.snapshot_id}</button>
    </section>
    <p role="status">{pending ? "Loading saved financials…" : saved.label}</p>
    <nav aria-label="Statements" className={styles.statementNav}>{saved.statements.map((statement) => <a key={statement.family} href={`#${statement.family}`}>{titles[statement.family]}</a>)}</nav>
    {saved.statements.map((statement) => <section id={statement.family} key={statement.family} className={styles.panel} data-statement={statement.family}>
      <div className={styles.heading}><h2>{titles[statement.family]}</h2><p>{statement.period.period_kind === "instant" ? `At ${statement.period.end_date}` : `${statement.period.start_date} – ${statement.period.end_date}`}</p></div>
      <p className={styles.coverage}>Selected lines · <EvidenceValue title={`${titles[statement.family]} · available lines`} value={statement.coverage.available} onInspect={(title) => inspect(title, undefined, statement)} /> / <EvidenceValue title={`${titles[statement.family]} · requested lines`} value={statement.coverage.requested} onInspect={(title) => inspect(title, undefined, statement)} /> available · USD</p>
      <div className={styles.tableWrap} role="region" aria-label={titles[statement.family]} tabIndex={0}><table><caption>{statement.period.period_kind === "instant" ? "Balances at period end" : "Reported flows for the stated duration"}</caption><thead><tr><th scope="col">Line item</th><th scope="col">Amount</th><th scope="col">Edition status</th></tr></thead><tbody>{statement.rows.map((row) => <tr key={row.concept} data-concept={row.concept} data-status={row.status}>
        <th scope="row">{row.label}</th><td><EvidenceValue title={row.label} value={row.value} display={number(row.value)} onInspect={() => inspect(row.label, row)} /></td>
        <td>{row.evidence.restatement_status === "unavailable" ? "N/A" : row.evidence.restatement_status === "repeated" ? "Unchanged" : row.evidence.restatement_status === "restated" ? "Restated" : "Original"}</td>
      </tr>)}</tbody></table></div>
    </section>)}
    <footer className={styles.footer}><Link href="/development/company" prefetch={false}>Company overview example</Link><Link href="/development/company/ratios" prefetch={false}>Fundamentals example</Link><Link href="/development/valuation" prefetch={false}>Reverse DCF example</Link><button className="text-button" onClick={() => inspect("Complete saved statements")}>Inspect full snapshot evidence</button></footer>
  </main><EvidenceDrawer detail={detail} onClose={() => setDetail(undefined)} /></WorkbenchShell>;
}
