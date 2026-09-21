import type { MonitoredFiling, MonitorSnapshot } from "./monitorTypes";
import styles from "./pipeline.module.css";

function Filing({ filing }: { filing: MonitoredFiling }) {
  return <details className={styles.disclosure}>
    <summary>{filing.form} · period ended {filing.reportDate ?? "Unknown"}<span className={styles.captureStatus}>Filed {filing.filedDate}</span></summary>
    <dl className={styles.facts}>
      <div><dt>Accession</dt><dd><code>{filing.accession}</code></dd></div>
      <div><dt>SEC acceptance (UTC)</dt><dd>{filing.acceptanceAt}</dd></div>
      <div><dt>Source capture (UTC)</dt><dd>{filing.capturedAt}</dd></div>
      <div><dt>Capture ID</dt><dd><code>{filing.captureId}</code></dd></div>
      <div><dt>Source locator</dt><dd><code>{filing.sourceLocator}</code></dd></div>
      <div><dt>Source SHA256</dt><dd><code>{filing.sha256}</code></dd></div>
    </dl>
    <a href={filing.url} target="_blank" rel="noreferrer">Open SEC Submissions source ↗</a>
  </details>;
}

const blockerLabels: Record<string, string> = {
  handoff_not_implemented: "Automatic analysis handoff is not implemented.",
  financial_coverage_not_reviewed: "Financial statement and event coverage still need review.",
  quote_registration_missing: "Quote registration still needs source evidence.",
};

export default function FilingMonitorPanel({ data }: { data: MonitorSnapshot }) {
  return <section className={styles.monitor} aria-labelledby="monitor-title" data-monitor-kind={data.kind}>
    <header className={styles.sectionHeading}><div><p className="eyebrow">FILING DISCOVERY / SAVED REAL CHECK</p><h2 id="monitor-title">SEC filing monitor</h2></div><span>D4a one-shot checkpoint · no background service</span></header>
    <div className={styles.monitorSummary}>
      <div><span className="eyebrow">OBSERVED RESULT</span><h3 data-monitor-outcome={data.outcome}>{data.outcomeLabel}</h3><p>{data.newCount} new filings · {data.amendmentCount} new amendments</p></div>
      <div><span className="eyebrow">CHECK COMPLETED (UTC)</span><p>{data.checkedAt ? <time dateTime={data.checkedAt}>{data.checkedAt}</time> : "No source check completed"}</p><p className={styles.note}>This is the attempt completion time. Reused source captures retain their original timestamps.</p></div>
    </div>
    <dl className={styles.facts}>
      <div><dt>Filed-date window</dt><dd>{data.filedStart} → {data.filedEnd}</dd></div>
      <div><dt>Acceptance cutoff (UTC)</dt><dd>{data.cutoff}</dd></div>
      <div><dt>Forms checked</dt><dd>{data.forms.join(", ")}</dd></div>
      <div><dt>Advertised inventory coverage</dt><dd>Baseline: {data.coverage.baseline} · Current: {data.coverage.current}</dd></div>
      <div><dt>Eligible comparison baseline</dt><dd>{data.baselineEligible ? "Yes · discovery only" : "No · resolve the recorded gaps"}</dd></div>
    </dl>
    {data.flags.length > 0 && <div className={styles.blocker}><h3>Check limitations</h3><ul>{data.flags.map((flag) => <li key={flag}><code>{flag}</code></li>)}</ul></div>}
    {data.newFilings.map((filing) => <Filing key={filing.accession} filing={filing} />)}
    {data.amendments.map((filing) => <Filing key={filing.accession} filing={filing} />)}
    <details className={styles.disclosure}><summary>Inspect {data.filingCount} scoped filings at the cutoff</summary>
      <p className={styles.note}>This list includes previously observed filings. An amendment is a separate filing edition; it does not itself establish a restatement or non-reliance event.</p>
      {data.filings.map((filing) => <Filing key={filing.accession} filing={filing} />)}
    </details>
    <details className={styles.disclosure}><summary>History coverage and excluded documents</summary>
      <p className={styles.note}>Only advertised documents whose filed-date ranges overlap the pinned window are required. Missing or malformed ranges prevent a complete check.</p>
      {(["baseline", "current"] as const).map((side) => <div key={side}><h3>{side === "baseline" ? "Baseline" : "Current"} inventory</h3>
        <p>Required history: {data.history[side]?.required.join(", ") || "None / unavailable; see coverage above"}</p>
        <p>Excluded outside the filed window: {data.history[side]?.excluded_nonoverlap.join(", ") || "None recorded"}</p>
      </div>)}
    </details>
    <details className={styles.disclosure}><summary>Baseline, request and retained response evidence</summary>
      <dl className={styles.facts}>
        <div><dt>Baseline source</dt><dd>{data.baseline.kind === "initial_seed" ? "Reviewed D3c acquisition" : "Prior complete monitor result"}</dd></div>
        <div><dt>Baseline request / execution</dt><dd><code>{data.baseline.requestId}</code><br /><code>{data.baseline.executionId}</code></dd></div>
        <div><dt>Baseline cutoff (UTC)</dt><dd>{data.baseline.cutoff}</dd></div>
        <div><dt>Baseline capture IDs</dt><dd>{data.baseline.captureIds.map((id) => <p key={id}><code>{id}</code></p>)}</dd></div>
        <div><dt>Baseline manifest SHA256</dt><dd><code>{data.baseline.manifestSha256}</code></dd></div>
        <div><dt>Monitor request / execution</dt><dd><code>{data.requestId}</code><br /><code>{data.executionId}</code></dd></div>
        <div><dt>Request SHA256</dt><dd><code>{data.requestSha256}</code></dd></div>
        <div><dt>Run manifest SHA256</dt><dd><code>{data.manifestSha256}</code></dd></div>
        <div><dt>Saved audit SHA256</dt><dd><code>{data.auditSha256}</code></dd></div>
      </dl>
      {data.attempts.map((attempt) => <div key={attempt.id} className={styles.monitorAttempt}><p>HTTP {attempt.status ?? "not received"} · <code>{attempt.state}</code></p><dl className={styles.facts}>
        <div><dt>Attempt ID</dt><dd><code>{attempt.id}</code></dd></div>
        <div><dt>Requested / finished (UTC)</dt><dd>{attempt.requestedAt ?? "Not dispatched"}<br />{attempt.finishedAt ?? "Not completed"}</dd></div>
        <div><dt>Reused capture</dt><dd><code>{attempt.reusedCaptureId ?? "New representation or unavailable"}</code></dd></div>
        <div><dt>New retained body</dt><dd>{attempt.payloadSha256 ? <><code>{attempt.payloadSha256}</code><br />{attempt.payloadBytes?.toLocaleString("en-US")} bytes</> : "No HTTP 200 body in this attempt"}</dd></div>
      </dl></div>)}
      <p className={styles.note}>Every complete HTTP 200 body is retained. Identical bytes can reuse a verified logical capture. HTTP 304 retains its conditional-response evidence without inventing a new body.</p>
    </details>
    <details className={styles.disclosure}><summary>Saved D4a totals after this filing check</summary><dl className={styles.counts}>{data.counts.map((count) => <div key={count.id} data-monitor-count={count.id}><dt>{count.label}</dt><dd>{count.value}</dd></div>)}</dl><p className={styles.note}>Previously saved evidence was verified unchanged. These totals include the filing-monitor request in addition to acquisition requests.</p></details>
    <div className={styles.monitorDisposition}><h3>Downstream analysis · not dispatched</h3><ul>{data.blockers.map((blocker) => <li key={blocker}>{blockerLabels[blocker] ?? blocker}</li>)}</ul></div>
    <p className={styles.note}>{data.knownLimits}</p>
  </section>;
}
