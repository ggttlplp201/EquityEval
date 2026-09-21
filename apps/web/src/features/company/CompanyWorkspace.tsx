"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import WorkbenchShell from "@/components/WorkbenchShell";
import EvidenceDrawer from "@/components/EvidenceDrawer";
import { PlotAxes } from "@/features/sectors/charts";
import type { CompanyMetric, CompanyPageData, SourceAmount } from "./types";
import styles from "./company.module.css";

function Metric({ metric, onDetail }: { metric: CompanyMetric | undefined; onDetail: (id: string) => void }) {
  if (!metric) return <p className={styles.unavailable}>Missing · no exported calculation.</p>;
  return <div className={styles.metric} data-metric-id={metric.id}>
    <div className={styles.metricHeading}><span>{metric.label}</span><Link href={`/help#${metric.id === "operating_margin" ? "operating-margin" : metric.id === "revenue_yoy" ? "yoy" : metric.id === "fcf_margin" ? "fcf" : metric.id}`} aria-label={`Definition of ${metric.label}`}>What is this?</Link></div>
    <button className={styles.metricValue} onClick={() => onDetail(metric.detailId)} aria-label={`${metric.label}: ${metric.valueLabel}. Inspect source evidence.`}>{metric.valueLabel}<span aria-hidden="true">↗</span></button>
    <span className={metric.status === "eligible" ? styles.status : styles.unavailable}>{metric.statusLabel}</span>
    <p>{metric.id === "pfcf" ? "Common equity market value / (trailing CFO − cash purchases of PPE). The company multiple requires positive FCF." : metric.id === "fcf_margin" ? "(CFO − cash purchases of PPE) / positive revenue, using matching trailing periods." : metric.definition}</p>
    {metric.reasons.length ? <p className={styles.unavailable}>{metric.reasons.join(" · ")}</p> : null}
  </div>;
}

function Amount({ amount, onDetail }: { amount: SourceAmount | undefined; onDetail: (id: string) => void }) {
  return amount ? <div className={styles.amount}><span>{amount.label}</span><button onClick={() => onDetail(amount.detailId)} className="text-button">{amount.valueLabel} ↗</button></div> : null;
}

export default function CompanyWorkspace({ data }: { data: CompanyPageData }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [historyWindow, setHistoryWindow] = useState("3");
  const [historyMetric, setHistoryMetric] = useState("operating_margin");
  const [detailId, setDetailId] = useState<string | null>(null);
  const view = data.views.find((item) => item.asOf === data.selectedAsOf)!;
  const history = view.history[historyWindow];
  const chart = history.charts[historyMetric];
  const metric = (id: string) => view.metrics.find((item) => item.id === id);
  const amount = (label: string) => view.amounts.find((item) => item.label === label);
  const selectedMetric = data.metrics.find((item) => item.id === historyMetric)!;
  const snapshots = [...data.views].sort((a, b) => a.asOf.localeCompare(b.asOf));
  function navigate(companyId: string, asOf: string) {
    setDetailId(null);
    startTransition(() => router.push(`/development/company?company=${encodeURIComponent(companyId)}&asOf=${encodeURIComponent(asOf)}`, { scroll: false }));
  }

  return <WorkbenchShell active="company" fictional>
    <main id="main-content" tabIndex={-1} className={styles.page} data-company-id={data.company.id} data-snapshot-id={view.snapshotId} data-view-id={view.id}>
      <div className={styles.intro}>
        <div><Link href="/development/sectors" className={styles.back}>← Sector Explorer</Link><p className="eyebrow">COMPANY RESEARCH / FICTIONAL EXAMPLE</p><h1>{data.company.name}</h1><p className={styles.identity}>{data.company.ticker} <span>·</span> {data.company.sectorLabel} <span>·</span> USD</p></div>
        <div className={styles.snapshot}><span className="eyebrow">COMPANY SNAPSHOT</span><code title={view.snapshotId}>{view.snapshotId.slice(0, 18)}</code><button className="text-button" onClick={() => setDetailId(view.detailId)}>Inspect source & calculation ↗</button></div>
      </div>
      <section className={styles.context} aria-label="Company calculation context" aria-busy={pending}>
        <label>Fictional company<select value={data.company.id} disabled={pending} onChange={(event) => navigate(event.target.value, data.selectedAsOf)}>{data.companies.map((item) => <option key={item.id} value={item.id}>{item.ticker} · {item.name}</option>)}</select></label>
        <label>Evaluation date<select value={data.selectedAsOf} disabled={pending} onChange={(event) => navigate(data.company.id, event.target.value)}>{data.context.asOfDates.map((date) => <option key={date}>{date}</option>)}</select></label>
        <div><span>Financial basis</span><strong>TTM · four exact calendar quarters</strong><small>Quarterly and annual views are not supplied.</small></div>
        <div><span>Price & filing freshness</span><strong>Fictional frozen inputs</strong><small>No live quote or real filing retrieval.</small></div>
      </section>
      <p className={styles.updateStatus} role="status">{pending ? "Loading the selected company snapshot…" : `Showing the frozen evaluation for ${data.selectedAsOf}. Monetary amounts are USD, without a millions or billions scale.`}</p>

      <div className={styles.sectionHeading}><div><span className="eyebrow">01 / THE FIVE-MINUTE REVIEW</span><h2>Understand the business in order</h2></div><Link href="/help#company">How to read this page ↗</Link></div>
      <div className={styles.reviewGrid}>
        <section className={styles.panel} aria-labelledby="growth-title"><div className={styles.panelTitle}><span>01</span><h3 id="growth-title">Growth</h3></div><Metric metric={metric("revenue_yoy")} onDetail={setDetailId} /><Amount amount={amount("TTM revenue")} onDetail={setDetailId} /><Amount amount={amount("Prior TTM revenue")} onDetail={setDetailId} /><p className={styles.question}>Is revenue expanding on a comparable reporting basis?</p></section>
        <section className={styles.panel} aria-labelledby="profitability-title"><div className={styles.panelTitle}><span>02</span><h3 id="profitability-title">Profitability</h3></div><Metric metric={metric("operating_margin")} onDetail={setDetailId} /><Amount amount={amount("TTM operating income")} onDetail={setDetailId} /><p className={styles.unavailable}>Gross and net margins unavailable: matching gross profit and consolidated net income were not supplied.</p><p className={styles.question}>How much revenue remains after operating costs?</p></section>
        <section className={styles.panel} aria-labelledby="cash-title"><div className={styles.panelTitle}><span>03</span><h3 id="cash-title">Cash generation</h3></div><Metric metric={metric("fcf_margin")} onDetail={setDetailId} /><Amount amount={amount("TTM CFO minus cash PPE purchases")} onDetail={setDetailId} /><p className={styles.unavailable}>Separate CFO and cash PPE operands are not available in this presentation. The supplied FCF retains its exact basis and source chain.</p><p className={styles.question}>How much cash remains after this defined capital spending?</p></section>
        <section className={styles.panel} aria-labelledby="balance-title"><div className={styles.panelTitle}><span>04</span><h3 id="balance-title">Balance sheet</h3></div><div className={styles.missingValue}>Missing inputs</div><p>Cash, debt, assets, liabilities and equity are not supplied in this company fixture. Liquidity, leverage and net debt cannot be shown.</p><p className={styles.unavailable}>Runway requires a separately reviewed method and eligible business context. Market capitalization is not a cash balance.</p><Link href="/help#cash-debt">Balance-sheet terminology ↗</Link><p className={styles.question}>What resources and obligations support the business?</p></section>
        <section className={`${styles.panel} ${styles.valuation}`} aria-labelledby="valuation-title"><div className={styles.panelTitle}><span>05</span><h3 id="valuation-title">Valuation context</h3></div><div className={styles.valuationMetrics}>{["pe", "ps", "pfcf"].map((id) => <Metric key={id} metric={metric(id)} onDetail={setDetailId} />)}</div><Amount amount={amount("Common equity market value")} onDetail={setDetailId} /><p className={styles.unavailable}>Price per share, EPS, forward P/E and a valuation range are unavailable here. These historical multiples are not an investment recommendation.</p><p className={styles.question}>What is the equity market value relative to comparable historical results?</p></section>
      </div>
      <details className={styles.returns}><summary>Returns on capital · additional inputs required</summary><p>ROA, ROE and ROIC are unavailable. The matching income basis, dated opening and closing balance-sheet amounts, and a reviewed invested-capital convention are not in this fixture. A sector classification does not establish whether a return metric is suitable for the business.</p><Link href="/help#returns">Understand the return measures ↗</Link></details>

      <section className={styles.history} aria-labelledby="history-title">
        <div className={styles.sectionHeading}><div><span className="eyebrow">02 / THROUGH TIME</span><h2 id="history-title">Company history</h2></div><div className="segmented compact" aria-label="Company history window">{["3", "5", "10"].map((years) => <button key={years} aria-pressed={historyWindow === years} onClick={() => setHistoryWindow(years)}>{years}Y</button>)}</div></div>
        <div className={styles.historyControls}><label>Measure<select value={historyMetric} onChange={(event) => setHistoryMetric(event.target.value)}>{data.metrics.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><div className={styles.coverage}><strong>Insufficient history</strong><span>{history.coverageLabel}</span><span>{history.windowStart} → {history.windowEnd}</span></div></div>
        <p className={styles.historyNote}>{history.note}</p>
        <div className="plot-scroll" tabIndex={0} role="region" aria-label="Scrollable company history chart"><svg className="analytical-plot" viewBox="-16 0 776 285" role="group" aria-label={`${selectedMetric.label}, ${historyWindow}-year requested window. ${history.coverageLabel}. Missing quarters remain gaps.`}>
          <title>{`${selectedMetric.label} · ${data.company.name}`}</title><desc>{`${history.note} The matching observations and their sources are in the table below.`}</desc>
          <PlotAxes xAxis={chart.xAxis} yAxis={chart.yAxis} />
          {chart.paths.map((path, index) => <path key={index} d={path} fill="none" stroke="var(--accent)" strokeWidth="2" />)}
          {chart.points.filter((point) => point.y !== null).map((point) => <circle key={point.date} cx={point.x} cy={point.y!} r="5" fill="var(--accent)" stroke="var(--bg)" strokeWidth="2" tabIndex={0} role="button" aria-label={`${point.date}: ${point.valueLabel}. Inspect source evidence.`} onClick={() => setDetailId(point.detailId)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setDetailId(point.detailId); } }}><title>{`${point.date} · ${point.valueLabel} · ${point.statusLabel}`}</title></circle>)}
        </svg></div>
        {chart.emptyReason ? <p className={styles.unavailable}>{chart.emptyReason}</p> : null}
        <details className={styles.historyTable}><summary>Observations, missing quarters & sources</summary><div className="table-scroll"><table><caption>{selectedMetric.label} · {data.company.name} · {historyWindow}-year requested window</caption><thead><tr><th>Snapshot date</th><th>Value</th><th>Status</th><th>Evidence</th></tr></thead><tbody>{chart.points.map((point) => <tr key={point.date} data-snapshot-id={point.snapshotId}><td>{point.date}</td><td>{point.valueLabel}</td><td>{point.statusLabel}{point.reasons.length ? ` · ${point.reasons.join(" · ")}` : ""}</td><td><button className="text-button" onClick={() => setDetailId(point.detailId)}>Inspect source ↗</button></td></tr>)}</tbody></table></div><p className={styles.missingDates}><strong>Missing quarter-end snapshots</strong><br />{history.missingDates.join(" · ") || "None"}</p>{chart.unavailableDates.length ? <p className={styles.unavailable}>Supplied snapshots without a usable value: {chart.unavailableDates.join(" · ")}</p> : null}<p className={styles.historyNote}>Historical rank, percentile and “cheap versus history” labels remain unavailable with this sample. The 5- and 10-year options are retained without filling missing periods.</p></details>
      </section>

      <div className={styles.evidenceGrid}>
        <section className={styles.evidencePanel} aria-labelledby="comparison-title"><span className="eyebrow">03 / COMPARE THE RECORD</span><h2 id="comparison-title">Saved snapshot values</h2><p>Compare the supplied results available by the selected evaluation date. Numerical attribution and business-cause explanations are not implemented.</p><div className="table-scroll"><table><caption className="sr-only">Company values by available snapshot</caption><thead><tr><th>Measure</th>{snapshots.map((snapshot) => <th key={snapshot.asOf}><button className="text-button" onClick={() => setDetailId(snapshot.detailId)}>{snapshot.asOf} ↗</button></th>)}</tr></thead><tbody>{data.metrics.map((item) => <tr key={item.id}><th scope="row">{item.label}</th>{snapshots.map((snapshot) => { const value = snapshot.metrics.find((entry) => entry.id === item.id); return <td key={snapshot.asOf}>{value ? <button className="text-button" title={value.statusLabel} onClick={() => setDetailId(value.detailId)}>{value.valueLabel}</button> : "Missing"}</td>; })}</tr>)}</tbody></table></div></section>
        <aside className={styles.reading}><span className="eyebrow">BUSINESS CONTEXT</span><h2>The right question depends on the business</h2><p>{data.company.sectorLabel} is an illustrative classification, not an evidenced business profile. No operating model, lifecycle or security-specific profile has been assigned to this fictional issuer.</p><p>Business profiles, expectations and earnings reviews remain planned. They will retain dated evidence and earlier versions when the analysis changes.</p><Link href="/help#profile">Read about profiles and research history ↗</Link><div className={styles.rule} /><p><strong>Watchlist additions & full reruns</strong><br />Real security resolution and the complete analysis workflow are not connected. Choosing a fictional company above only opens its saved demonstration results.</p></aside>
      </div>
      <section className={styles.sourceAmounts} aria-labelledby="amounts-title"><div className={styles.sectionHeading}><div><span className="eyebrow">04 / THE INPUTS BEHIND THE RESULTS</span><h2 id="amounts-title">Source amounts</h2></div><button className="secondary-button" onClick={() => setDetailId(view.detailId)}>Open complete evidence ↗</button></div><p>Exact supplied amounts in USD. Each row keeps its own reporting period and scope; common-shareholder income is not silently substituted for consolidated net income.</p><div className="table-scroll"><table><caption className="sr-only">Financial source amounts for {data.selectedAsOf}</caption><thead><tr><th>Amount</th><th>Value</th><th>Period</th><th>Basis</th><th>Flags</th></tr></thead><tbody>{view.amounts.map((entry) => <tr key={entry.label} data-input-hash={entry.inputHash}><th scope="row">{entry.label}</th><td><button className="text-button" onClick={() => setDetailId(entry.detailId)}>{entry.valueLabel}</button></td><td>{entry.period}</td><td>{entry.basis}</td><td>{entry.flags}</td></tr>)}</tbody></table></div></section>
      <footer className={styles.footer}><span>FICTIONAL SNAPSHOT · {data.selectedAsOf} · USD</span><Link href="/sectors">Review real-data prerequisites ↗</Link></footer>
    </main>
    <EvidenceDrawer detail={detailId ? data.details[detailId] : undefined} onClose={() => setDetailId(null)} />
  </WorkbenchShell>;
}
