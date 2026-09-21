"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import WorkbenchShell from "@/components/WorkbenchShell";
import EvidenceDrawer from "@/components/EvidenceDrawer";
import type { PilotFiling, PilotHistoryWindow, PilotMetric, PilotPageData } from "./types";
import companyStyles from "@/features/company/company.module.css";
import styles from "./pilot.module.css";

function FilingReference({ filing }: { filing: PilotFiling }) {
  return <dl className={styles.filingFields}>
    <div><dt>Form</dt><dd>{filing.form}</dd></div>
    <div><dt>Period ended</dt><dd>{filing.periodEnd}</dd></div>
    <div><dt>Filed</dt><dd>{filing.filed}</dd></div>
    <div><dt>Accession</dt><dd><a href={filing.url} target="_blank" rel="noreferrer">{filing.accession} ↗</a></dd></div>
  </dl>;
}

function UnavailableMetric({ metric, onDetail }: { metric: PilotMetric; onDetail: (id: string) => void }) {
  return <article className={styles.metric} data-metric-id={metric.id}>
    <h3>{metric.label}</h3><p className={styles.unavailableValue}>{metric.valueLabel}</p>
    <p className={styles.status}>{metric.statusLabel}</p>
    <ul>{metric.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
    {metric.detailId ? <button type="button" className="text-button" onClick={() => onDetail(metric.detailId!)}>Inspect available evidence ↗</button> : null}
  </article>;
}

export default function PilotWorkspace({ data }: { data: PilotPageData }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [historyWindow, setHistoryWindow] = useState<PilotHistoryWindow>("3");
  const [detailId, setDetailId] = useState<string | null>(null);
  const company = data.company;
  const history = company.history[historyWindow];
  function navigate(ticker: string) {
    setDetailId(null);
    startTransition(() => router.push(`/development/pilot?company=${encodeURIComponent(ticker)}`, { scroll: false }));
  }

  return <WorkbenchShell active="pilot">
    <main id="main-content" tabIndex={-1} className={`${companyStyles.page} ${styles.page}`} data-pilot-ticker={company.ticker} data-snapshot-id={data.snapshotId}>
      <div className={companyStyles.intro}>
        <div><p className="eyebrow">REAL-DATA PILOT / ARCHIVED SEC EVIDENCE</p><h1>{company.name}</h1><p className={companyStyles.identity}>{company.ticker} <span>·</span> {company.exchange} <span>·</span> CIK {company.cik}</p></div>
        <div className={`${companyStyles.snapshot} ${styles.snapshot}`}><span className="eyebrow">ARCHIVED PILOT SNAPSHOT</span><code title={data.snapshotId}>{data.snapshotId}</code><span>Reviewed {data.reviewedAt}</span></div>
      </div>
      <section className={styles.notice} aria-label="Pilot scope"><strong>Real sources. Incomplete financial coverage.</strong><p>This page presents archived source observations and the evidence behind them. It is not a current valuation, live quote service or completed analysis. The seven selected companies are neither a complete sector universe nor a comparable peer group.</p></section>
      <section className={styles.context} aria-label="Selected security and evidence" aria-busy={pending}>
        <label>Selected pilot company<select value={company.ticker} disabled={pending} onChange={(event) => navigate(event.target.value)}>{data.roster.map((item) => <option key={item.ticker} value={item.ticker}>{item.ticker} · {item.name}</option>)}</select></label>
        <div><span>Security in dated filing</span><strong>{company.security}</strong><a href={company.identityUrl} target="_blank" rel="noreferrer">Identity evidence · {company.identityDate} ↗</a></div>
        <div><span>Price & source freshness</span><strong>No live prices</strong><small>Report periods, filing dates and archive capture times remain separate.</small></div>
      </section>
      <p className={companyStyles.updateStatus} role="status">{pending ? "Opening the selected pilot evidence…" : company.observedFiling ? `Showing ${company.ticker}'s archived observations. Other companies’ financial observations are not substituted.` : `Showing ${company.ticker}'s dated research references; financial observations are not supplied.`}</p>

      <div className={companyStyles.sectionHeading}><div><span className="eyebrow">01 / FOLLOW THE SOURCE</span><h2>Research context and observed amounts</h2></div><Link href="/help#real-source-pilot">How to read the pilot ↗</Link></div>
      <div className={styles.filingGrid}>
        <section className={styles.panel} aria-labelledby="research-filing-title"><span className="eyebrow">RESEARCH REFERENCE</span><h3 id="research-filing-title">Filing reviewed for context</h3><FilingReference filing={company.filing} /><p className={styles.note}>This reference identifies the filing used for company research. Its presence does not mean that its financial values have been extracted or qualified for this pilot.</p></section>
        <section className={styles.panel} aria-labelledby="observed-filing-title"><span className="eyebrow">OBSERVED FINANCIAL SOURCE</span><h3 id="observed-filing-title">Filing behind the displayed amounts</h3>
          {company.observedFiling ? <><FilingReference filing={company.observedFiling} /><dl className={styles.filingFields}><div><dt>Period started</dt><dd>{company.observedFiling.periodStart}</dd></div><div><dt>Filing captured</dt><dd>{company.observedFiling.capturedAt}</dd></div><div><dt>Company Facts captured</dt><dd>{company.observedFiling.companyfactsCapturedAt}</dd></div></dl><p className={styles.note}>These amounts belong to this observed filing and period. A newer research reference does not relabel them as current or extend their coverage.</p></> : <div className={styles.empty}><strong>No qualified financial observations supplied</strong><p>Identity and business research are available. Financial amounts from the reference filing have not been supplied to this snapshot; this is a coverage gap, not a reported zero.</p></div>}
        </section>
      </div>
      <section className={styles.business} aria-labelledby="business-title"><div><span className="eyebrow">DATED BUSINESS CONTEXT</span><h2 id="business-title">Understand the instrument and operating model</h2></div><p>{company.businessSummary}</p><a href={company.businessEvidenceUrl} target="_blank" rel="noreferrer">Business evidence · {company.businessEvidenceDate} ↗</a><p className={styles.note}>This research summary is not an activated metric-applicability policy or saved profile version. Segment, lifecycle and instrument definitions still govern which later calculations can be supported.</p></section>

      <section className={companyStyles.sourceAmounts} aria-labelledby="amounts-title"><div className={companyStyles.sectionHeading}><div><span className="eyebrow">02 / ARCHIVED OBSERVATIONS</span><h2 id="amounts-title">Source amounts</h2></div><Link href="/help#provenance">Read the source chain ↗</Link></div><p>Only supplied observations appear below. Open a value for its exact source, reported concept, units, period and recorded transformation. An observation can be inspectable while a dependent calculation remains unavailable.</p>
        {company.amounts.length ? <div className="table-scroll" tabIndex={0} role="region" aria-label="Archived source amounts; scroll horizontally on smaller screens"><table className={styles.amountTable}><caption>Archived observations for {company.ticker}; retain each source period</caption><thead><tr><th scope="col">Source amount</th><th scope="col">Value</th><th scope="col">Reporting period</th><th scope="col">Status</th></tr></thead><tbody>{company.amounts.map((amount) => <tr key={amount.id} data-amount-id={amount.id}><th scope="row">{amount.label}</th><td><button type="button" className="text-button" onClick={() => setDetailId(amount.detailId)} aria-label={`${amount.label}: ${amount.valueLabel}. Inspect archived source.`}>{amount.valueLabel} ↗</button></td><td>{amount.period}</td><td>{amount.statusLabel}</td></tr>)}</tbody></table></div> : <div className={styles.empty}><strong>No source amounts in this pilot snapshot</strong><p>Missing inputs remain visible. No demonstration values, estimates or zero substitutions are used for {company.ticker}.</p></div>}
      </section>

      <section aria-labelledby="metrics-title"><div className={companyStyles.sectionHeading}><div><span className="eyebrow">03 / CALCULATION READINESS</span><h2 id="metrics-title">What is still unavailable</h2></div><Link href="/help#missing">Understanding gaps ↗</Link></div><p className={styles.sectionNote}>These metrics have no result in this source-only slice. Raw amounts do not establish compatible periods, sufficient inputs, instrument scope or a reviewed calculation policy.</p><div className={styles.metrics}>{company.metrics.map((metric) => <UnavailableMetric key={metric.id} metric={metric} onDetail={setDetailId} />)}</div></section>

      <section className={companyStyles.history} aria-labelledby="history-title"><div className={companyStyles.sectionHeading}><div><span className="eyebrow">04 / LONGER HISTORY</span><h2 id="history-title">Keep the requested window visible</h2></div><div className="segmented compact" aria-label="Pilot company history window">{(["3", "5", "10"] as const).map((years) => <button type="button" key={years} aria-pressed={historyWindow === years} onClick={() => setHistoryWindow(years)}>{years}Y</button>)}</div></div><div className={styles.historySummary} aria-live="polite"><strong>{history.coverageLabel}</strong><span>{history.windowStart} → {history.windowEnd}</span><p>{history.note}</p></div><div className={styles.noChart}><span className="eyebrow">NO QUALIFIED COMPARISON SERIES</span><p>No historical graph, percentile or rank is produced. A longer selected window does not create missing observations or borrow fictional Sector Explorer history.</p></div></section>

      <section aria-labelledby="coverage-title"><div className={companyStyles.sectionHeading}><div><span className="eyebrow">05 / THE SEVEN-COMPANY PILOT</span><h2 id="coverage-title">Coverage and applicability gaps</h2></div><Link href="/sectors">Sector production prerequisites ↗</Link></div><p className={styles.sectionNote}>Select a company to inspect its own source evidence. These are per-company readiness gaps, not sector coverage scores or investment rankings.</p><div className={styles.roster}>{data.roster.map((item) => <article className={`${styles.rosterRow} ${item.ticker === company.ticker ? styles.selected : ""}`} key={item.ticker}><header><Link href={`/development/pilot?company=${item.ticker}`} aria-current={item.ticker === company.ticker ? "page" : undefined}>{item.ticker} <span>↗</span></Link><span>{item.name}</span><p>{item.hasObservedAmounts ? "Limited archived observations" : "Financial observations not supplied"}</p></header><dl>{item.gaps.map((gap) => <div key={gap.area}><dt>{gap.area}</dt><dd>{gap.reason}</dd></div>)}</dl></article>)}</div></section>
      <footer className={companyStyles.footer}><span>REAL SOURCE PILOT · ARCHIVED OBSERVATIONS · NO LIVE PRICES</span><Link href="/development/company" prefetch={false}>Open the separate fictional demonstration ↗</Link></footer>
    </main>
    <EvidenceDrawer detail={detailId ? data.details[detailId] : undefined} onClose={() => setDetailId(null)} eyebrow="ARCHIVED SEC EVIDENCE · REAL SOURCE PILOT" />
  </WorkbenchShell>;
}
