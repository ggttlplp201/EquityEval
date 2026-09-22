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
    <h3>{metric.label}</h3><p className={styles.unavailableValue}>N/A</p>
    {metric.detailId ? <button type="button" className="text-button" onClick={() => onDetail(metric.detailId!)}>Source details ↗</button> : null}
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
      <p className={styles.pipelineLink}><Link href="/development/pilot/pipeline">Inspect CRCL’s application pipeline ↗</Link></p>
      <section className={styles.context} aria-label="Selected security and evidence" aria-busy={pending}>
        <label>Selected pilot company<select value={company.ticker} disabled={pending} onChange={(event) => navigate(event.target.value)}>{data.roster.map((item) => <option key={item.ticker} value={item.ticker}>{item.ticker} · {item.name}</option>)}</select></label>
        <div><span>Security in dated filing</span><strong>{company.security}</strong><a href={company.identityUrl} target="_blank" rel="noreferrer">Identity evidence · {company.identityDate} ↗</a></div>
        <div><span>Price</span><strong>N/A</strong></div>
      </section>
      <p className={companyStyles.updateStatus} role="status">{pending ? "Opening the selected pilot evidence…" : `Showing ${company.ticker}`}</p>

      <div className={companyStyles.sectionHeading}><div><span className="eyebrow">01 / FOLLOW THE SOURCE</span><h2>Research context and observed amounts</h2></div><Link href="/help#real-source-pilot">How to read the pilot ↗</Link></div>
      <div className={styles.filingGrid}>
        <section className={styles.panel} aria-labelledby="research-filing-title"><span className="eyebrow">RESEARCH REFERENCE</span><h3 id="research-filing-title">Filing reviewed for context</h3><FilingReference filing={company.filing} /></section>
        <section className={styles.panel} aria-labelledby="observed-filing-title"><span className="eyebrow">OBSERVED FINANCIAL SOURCE</span><h3 id="observed-filing-title">Filing behind the displayed amounts</h3>
          {company.observedFiling ? <><FilingReference filing={company.observedFiling} /><dl className={styles.filingFields}><div><dt>Period started</dt><dd>{company.observedFiling.periodStart}</dd></div><div><dt>Filing captured</dt><dd>{company.observedFiling.capturedAt}</dd></div><div><dt>Company Facts captured</dt><dd>{company.observedFiling.companyfactsCapturedAt}</dd></div></dl></> : <div className={styles.empty}>N/A</div>}
        </section>
      </div>
      <section className={styles.business} aria-labelledby="business-title"><div><span className="eyebrow">DATED BUSINESS CONTEXT</span><h2 id="business-title">Understand the instrument and operating model</h2></div><p>{company.businessSummary}</p><a href={company.businessEvidenceUrl} target="_blank" rel="noreferrer">Business evidence · {company.businessEvidenceDate} ↗</a></section>

      <section className={companyStyles.sourceAmounts} aria-labelledby="amounts-title"><div className={companyStyles.sectionHeading}><div><span className="eyebrow">02 / ARCHIVED OBSERVATIONS</span><h2 id="amounts-title">Source amounts</h2></div><Link href="/help#provenance">Read the source chain ↗</Link></div>
        {company.amounts.length ? <div className="table-scroll" tabIndex={0} role="region" aria-label="Archived source amounts; scroll horizontally on smaller screens"><table className={styles.amountTable}><caption>Archived observations for {company.ticker}; retain each source period</caption><thead><tr><th scope="col">Source amount</th><th scope="col">Value</th><th scope="col">Reporting period</th><th scope="col">Status</th></tr></thead><tbody>{company.amounts.map((amount) => <tr key={amount.id} data-amount-id={amount.id}><th scope="row">{amount.label}</th><td><button type="button" className="text-button" onClick={() => setDetailId(amount.detailId)} aria-label={`${amount.label}: ${amount.value === null ? "N/A" : amount.valueLabel}. Inspect archived source.`}>{amount.value === null ? "N/A" : amount.valueLabel} ↗</button></td><td>{amount.period}</td><td>{amount.value === null ? "N/A" : "Observed"}</td></tr>)}</tbody></table></div> : <div className={styles.empty}>N/A</div>}
      </section>

      <section aria-labelledby="metrics-title"><div className={companyStyles.sectionHeading}><div><span className="eyebrow">03 / FUNDAMENTALS</span><h2 id="metrics-title">Key metrics</h2></div><Link href="/help">Metric guide ↗</Link></div><div className={styles.metrics}>{company.metrics.map((metric) => <UnavailableMetric key={metric.id} metric={metric} onDetail={setDetailId} />)}</div></section>

      <section className={companyStyles.history} aria-labelledby="history-title"><div className={companyStyles.sectionHeading}><div><span className="eyebrow">04 / LONGER HISTORY</span><h2 id="history-title">Historical trends</h2></div><div className="segmented compact" aria-label="Pilot company history window">{(["3", "5", "10"] as const).map((years) => <button type="button" key={years} aria-pressed={historyWindow === years} onClick={() => setHistoryWindow(years)}>{years}Y</button>)}</div></div><div className={styles.historySummary} aria-live="polite"><span>{history.windowStart} → {history.windowEnd}</span></div><div className={styles.noChart}><span className={styles.unavailableValue}>N/A</span></div></section>

      <section aria-labelledby="coverage-title"><div className={companyStyles.sectionHeading}><div><span className="eyebrow">05 / THE SEVEN-COMPANY PILOT</span><h2 id="coverage-title">Companies</h2></div><Link href="/sectors">Sector Explorer ↗</Link></div><div className={styles.roster}>{data.roster.map((item) => <article className={`${styles.rosterRow} ${item.ticker === company.ticker ? styles.selected : ""}`} key={item.ticker}><header><Link href={`/development/pilot?company=${item.ticker}`} aria-current={item.ticker === company.ticker ? "page" : undefined}>{item.ticker} <span>↗</span></Link><span>{item.name}</span><p>{item.hasObservedAmounts ? "Archived observations" : "N/A"}</p></header><dl>{item.gaps.map((gap) => <div key={gap.area}><dt>{gap.area}</dt><dd>N/A</dd></div>)}</dl></article>)}</div></section>
      <footer className={companyStyles.footer}><span>ARCHIVED SEC OBSERVATIONS</span><Link href="/development/company" prefetch={false}>Open the separate fictional demonstration ↗</Link></footer>
    </main>
    <EvidenceDrawer detail={detailId ? data.details[detailId] : undefined} onClose={() => setDetailId(null)} eyebrow="ARCHIVED SEC EVIDENCE · REAL SOURCE PILOT" />
  </WorkbenchShell>;
}
