"use client";

import Link from "next/link";
import { useState } from "react";
import FilingSchedulePanel from "./FilingSchedulePanel";
import schedulerSnapshot from "./schedulerSnapshot";
import FilingMonitorPanel from "./FilingMonitorPanel";
import monitorSnapshot from "./monitorSnapshot";
import WorkbenchShell from "@/components/WorkbenchShell";
import type { PipelineCapture, PipelineEvidence, PipelineSnapshot, PipelineStageId } from "./types";
import styles from "./pipeline.module.css";

function Evidence({ items, captures }: { items: PipelineEvidence[]; captures: PipelineCapture[] }) {
  return <ul className={styles.evidenceList}>{items.map((item) => {
    const capture = captures.find((source) => source.id === item.captureId);
    if (!capture) throw new Error("Pipeline evidence is missing its source capture.");
    return <li key={`${item.captureId}:${item.locator}`}>
      <a href={capture.url} target="_blank" rel="noreferrer">SEC · {capture.label} ↗</a>
      <blockquote>{item.excerpt}</blockquote>
      <dl className={styles.facts}>
        <div><dt>Source locator</dt><dd><code>{item.locator}</code></dd></div>
        <div><dt>Captured (UTC)</dt><dd><time dateTime={capture.capturedAt}>{capture.capturedAt}</time></dd></div>
        <div><dt>Capture ID</dt><dd><code>{capture.id}</code></dd></div>
        <div><dt>Body SHA256</dt><dd><code>{capture.sha256}</code></dd></div>
      </dl>
    </li>;
  })}</ul>;
}

function StageContent({ selected, data }: { selected: PipelineStageId; data: PipelineSnapshot }) {
  if (selected === "plan") return <>
    <dl className={styles.facts}>
      <div><dt>Source scope</dt><dd>{data.plan.policy}</dd></div>
      <div><dt>Inventory window</dt><dd>{data.plan.inventoryStart} → {data.plan.inventoryEnd}</dd></div>
      <div><dt>Request type</dt><dd>Source bootstrap · acquisition only</dd></div>
    </dl>
    <details className={styles.disclosure}><summary>Inspect the five pinned resources</summary>
      <ul>{data.plan.resources.map((resource) => <li key={resource}>{resource}</li>)}</ul>
      <p>The inventory window limits filing discovery. It is not a claim of financial-history coverage.</p>
      <dl className={styles.facts}><div><dt>Request parameters SHA256</dt><dd><code>{data.plan.hash}</code></dd></div></dl>
    </details>
  </>;
  if (selected === "captures") return <>
    <p className={styles.note}>These are the five captures in the pinned acquisition request, within 12 application captures at the D3f checkpoint. Source collection does not establish complete statement or event coverage.</p>
    <div>{data.captures.map((capture) => <details className={styles.disclosure} key={capture.id}>
      <summary>{capture.label} <span className={styles.captureStatus}>HTTP {capture.httpStatus}</span></summary>
      <a href={capture.url} target="_blank" rel="noreferrer">Open public SEC source ↗</a>
      <dl className={styles.facts}>
        <div><dt>Requested (UTC)</dt><dd><time dateTime={capture.requestedAt}>{capture.requestedAt}</time></dd></div>
        <div><dt>Captured (UTC)</dt><dd><time dateTime={capture.capturedAt}>{capture.capturedAt}</time></dd></div>
        <div><dt>Archived bytes</dt><dd>{capture.bytes.toLocaleString("en-US")}</dd></div>
        <div><dt>Capture ID</dt><dd><code>{capture.id}</code></dd></div>
        <div><dt>Body SHA256</dt><dd><code>{capture.sha256}</code></dd></div>
      </dl>
    </details>)}</div>
  </>;
  if (selected === "identity") return <>
    <p className={styles.note}>Supported fields are reviewed candidates. They have not created a quote identifier. NYSE is the SEC exchange code; no MIC conversion is assumed.</p>
    <dl className={styles.identityFields}>{data.identityFields.map((field) => <div key={field.id} data-identity-field={field.id}>
      <dt>{field.label}</dt><dd><span className={field.value === null ? styles.missing : styles.fieldValue}>{field.value ?? "Unsubstantiated"}</span>
        {field.evidence.length > 0 ? <details className={styles.disclosure}>
          <summary>{field.label} evidence · supported</summary>
          <Evidence items={field.evidence} captures={data.captures} />
        </details> : <p className={styles.note}>No explicit quotation-currency evidence in this review. The value remains missing.</p>}
      </dd>
    </div>)}</dl>
    <p className={styles.note}>Listing start comes from an explicit statement in the annual report. It is not the filing date, reporting-period end, holder-observation date or capture time.</p>
    <details className={styles.disclosure}><summary>Why reporting currency does not resolve the gap</summary>
      <p>USD financial reporting and USD/share offering prices describe different facts from the exchange quotation currency. They are not substitutes for the missing evidence.</p>
      <Evidence items={data.reportingCurrencyEvidence} captures={data.captures} />
    </details>
  </>;
  if (selected === "registration") return <>
    <div className={styles.blocker}>
      <span className="eyebrow">REQUIRED EVIDENCE MISSING</span><h3>{data.blocker.title}</h3>
      <p>{data.blocker.explanation}</p>
    </div>
    <section className={styles.search} aria-labelledby="currency-search-title">
      <h3 id="currency-search-title">Official-source search</h3>
      <p>{data.currencySearch.summary}</p>
      <p className={styles.note}>Reviewed <time dateTime={data.currencySearch.reviewedOn}>{data.currencySearch.reviewedOn}</time>. {data.currencySearch.basis}</p>
      {data.currencySearch.sources.map((source) => <details className={styles.disclosure} key={source.id} data-search-source={source.id}>
        <summary>{source.label}<span className={styles.searchStatus}>{source.statusLabel}</span></summary>
        <p>{source.finding}</p>
        <dl className={styles.facts}>
          <div><dt>How checked</dt><dd>{source.method}</dd></div>
          <div><dt>Date context</dt><dd>{source.dateContext}</dd></div>
          <div><dt>Retention / source policy</dt><dd>{source.policy}</dd></div>
        </dl>
        <ul className={styles.searchLinks}>
          <li><a href={source.url} target="_blank" rel="noreferrer">{source.label} ↗</a></li>
          {source.links.map((link) => <li key={link.url}><a href={link.url} target="_blank" rel="noreferrer">{link.label} ↗</a></li>)}
        </ul>
      </details>)}
      <p className={styles.note}>{data.currencySearch.effectiveDateRule}</p>
      <p className={styles.note}>Search notes added no application captures or source policies. The acquisition totals above describe that checkpoint; the filing-monitor section records later activity.</p>
    </section>
    <details className={styles.disclosure}><summary>What the blocked check means</summary>
      <p>The repeatable identity check returned a blocked result. The saved application has zero quote identifiers and zero watchlist memberships. Issuer and security records already exist; they are not the same as a registered exchange quote.</p>
      <p className={styles.note}>Recorded reason: <code>{data.blocker.code}</code></p>
    </details>
  </>;
  if (selected === "normalization") return <div className={styles.unstarted}>
    <h3>Source bodies are available; financial facts are not published.</h3>
    <p>The application has zero normalization batches. Financial statement and event coverage, reviewed mappings and point-in-time eligibility still need review.</p>
    <p>The older archived observations on the pilot page are a separate research artifact. They do not populate or complete this application stage.</p>
    <Link href="/development/pilot?company=CRCL">Inspect the separate archived observations ↗</Link>
  </div>;
  return <div className={styles.unstarted}>
    <h3>No financial-analysis result</h3>
    <p>The three acquisition requests are bootstraps. The separate filing check discovers source changes only. Ordinary analysis has not started, and no financial result has been published from them.</p>
    <p>Quote registration alone would not establish complete financial coverage, add a watchlist membership or publish an analysis. Those prerequisites remain separate.</p>
  </div>;
}

export default function PipelineWorkspace({ data }: { data: PipelineSnapshot }) {
  const [selected, setSelected] = useState<PipelineStageId>("registration");
  const stage = data.stages.find((item) => item.id === selected)!;
  return <WorkbenchShell active="pilot">
    <main id="main-content" tabIndex={-1} className={styles.page} data-pipeline-kind={data.kind}>
      <Link href="/development/pilot?company=CRCL" className={styles.back}>← Archived company observations</Link>
      <header className={styles.intro}>
        <div><p className="eyebrow">REAL APPLICATION STATE / CRCL</p><h1>From source to analysis<span aria-hidden="true">.</span></h1><p>Inspect source collection, filing discovery and the evidence still needed for analysis.</p></div>
        <div className={styles.stamp}><strong>Saved snapshot · {data.reviewedOn}</strong><span>D3c acquisition / D3f search / D4a filing check / D4b schedule</span><span>Read-only preview · not a live status service</span></div>
      </header>
      <section className={styles.boundary} aria-label="Application snapshot scope">
        <strong>Acquisition readiness is not financial-analysis readiness.</strong>
        <p>This saved state comes from real application audits. It is separate from the fictional company/sector demonstrations and the pilot’s older archived financial observations. It contains no financial-analysis result.</p>
      </section>
      <section aria-labelledby="totals-title">
        <div className={styles.sectionHeading}><h2 id="totals-title">Saved application totals</h2><span>D3f acquisition checkpoint · before the filing check</span></div>
        <dl className={styles.counts}>{data.counts.map((count) => <div key={count.id} data-count={count.id}><dt>{count.label}</dt><dd>{count.value}</dd></div>)}</dl>
      </section>
      <FilingSchedulePanel data={schedulerSnapshot} />
      <FilingMonitorPanel data={monitorSnapshot} />
      <div className={styles.sectionHeading}><h2 id="stages-title">Inspect each stage</h2><span>Select a stage, then expand its evidence.</span></div>
      <div className={styles.workflow}>
        <nav aria-labelledby="stages-title" className={styles.stageNav}><ol>{data.stages.map((item) => <li key={item.id}>
          <button type="button" aria-pressed={selected === item.id} aria-controls="stage-panel" data-stage={item.id} data-state={item.status} onClick={() => setSelected(item.id)}>
            <span className={styles.stepNumber} aria-hidden="true">{item.number}</span>
            <span><strong>{item.label}</strong><small>{item.statusLabel}</small></span>
            <span className={styles.stageArrow} aria-hidden="true">↗</span>
          </button>
        </li>)}</ol></nav>
        <section id="stage-panel" aria-labelledby="stage-title" tabIndex={0} className={styles.stagePanel}>
          <p className="sr-only" role="status">{stage.label}: {stage.statusLabel}</p>
          <header className={styles.stageHeader}><span className="eyebrow">STAGE {stage.number}</span><span className={styles.badge} data-state={stage.status}>{stage.statusLabel}</span><h2 id="stage-title">{stage.label}</h2><p>{stage.summary}</p></header>
          <div key={selected}><StageContent selected={selected} data={data} /></div>
        </section>
      </div>
      <aside className={styles.nextAction} aria-labelledby="next-action-title"><div><p className="eyebrow">NEXT STEP / BLOCKED</p><h2 id="next-action-title">Evidence before registration</h2></div><p>{data.blocker.nextAction}</p><p className={styles.note}>This preview does not fetch sources, retry requests or change registrations.</p></aside>
      <details className={`${styles.disclosure} ${styles.audit}`}><summary>Snapshot provenance and audit references</summary>
        <p>Generated from the checked D3c/D3d audit artifacts and D3f research notes. Capture hashes identify archived SEC evidence. Search links identify inspected sources; research notes are not archived source payloads.</p>
        <dl className={styles.facts}>
          <div><dt>Identity checkpoint</dt><dd>{data.reviewCheckpoint}</dd></div>
          <div><dt>Acquisition verified (UTC)</dt><dd><time dateTime={data.acquisitionVerifiedAt}>{data.acquisitionVerifiedAt}</time></dd></div>
          <div><dt>Request ID</dt><dd><code>{data.requestId}</code></dd></div>
          <div><dt>Execution ID</dt><dd><code>{data.executionId}</code></dd></div>
          <div><dt>Acquisition audit SHA256</dt><dd><code>{data.acquisitionAuditSha256}</code></dd></div>
          <div><dt>Identity audit SHA256</dt><dd><code>{data.identityAuditSha256}</code></dd></div>
          <div><dt>Search notes SHA256</dt><dd><code>{data.currencySearch.sha256}</code></dd></div>
        </dl>
      </details>
      <footer className={styles.footer}><span>SAVED APPLICATION STATE · NO PUBLISHED FINANCIAL RESULT</span><Link href="/sectors">Data readiness ↗</Link></footer>
    </main>
  </WorkbenchShell>;
}
