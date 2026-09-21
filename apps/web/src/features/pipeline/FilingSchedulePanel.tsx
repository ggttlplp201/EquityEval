import type { SchedulerSnapshot } from "./schedulerTypes";
import styles from "./pipeline.module.css";

function Time({ value }: { value: string | null }) {
  return value ? <time dateTime={value}>{value}</time> : <>Not recorded</>;
}

export default function FilingSchedulePanel({ data }: { data: SchedulerSnapshot }) {
  return <section className={styles.monitor} aria-labelledby="schedule-title" data-schedule-kind={data.kind}>
    <header className={styles.sectionHeading}><div><p className="eyebrow">SCHEDULING / SAVED MANUAL CHECK</p><h2 id="schedule-title">Filing schedule</h2></div><span>Background service not configured</span></header>
    <div className={styles.monitorSummary}>
      <div><span className="eyebrow">CONFIGURATION</span><h3 data-schedule-state={data.active ? "active" : "paused"}>{data.active ? "Active configuration" : "Paused"}</h3><p>Health: <code>{data.health}</code> · revision {data.epoch}</p></div>
      <div><span className="eyebrow">SAVED AS OF (UTC)</span><p><Time value={data.asOf} /></p><p className={styles.note}>{data.healthMeaning} Opening this page does not run a check.</p></div>
    </div>
    <dl className={styles.facts}>
      <div><dt>Fixed filed-date window</dt><dd>{data.filedStart} → {data.filedEnd}</dd></div>
      <div><dt>Cadence / bounded jitter</dt><dd>{data.cadenceSeconds} seconds / {data.jitterSeconds} seconds</dd></div>
      <div><dt>Last tick (UTC)</dt><dd><Time value={data.lastTickAt} /></dd></div>
      <div><dt>Last HTTP completion (UTC)</dt><dd><Time value={data.lastHttpCompletedAt} /></dd></div>
      <div><dt>Last eligible success (UTC)</dt><dd><Time value={data.lastSuccessAt} /></dd></div>
      <div><dt>Last successful acceptance cutoff</dt><dd><Time value={data.lastSuccessCutoff} /></dd></div>
      <div><dt>Next scheduled slot (UTC)</dt><dd><Time value={data.nextDueAt} /><br />{data.nextDueActionable ? "Subject to due time, budget and worker checks" : "Not actionable in the saved state"}</dd></div>
      <div><dt>Lag / consecutive failed polls</dt><dd>{data.lagSeconds} seconds / {data.failures}</dd></div>
      <div><dt>Reserved attempt allowance</dt><dd>{data.reservedUnits} / {data.budgetUnits} units</dd></div>
      <div><dt>Recorded dispatch attempts</dt><dd data-schedule-attempts>{data.actualAttempts}</dd></div>
      <div><dt>Retry gate (UTC)</dt><dd><Time value={data.retryAt} /></dd></div>
    </dl>
    <p className={styles.note}>The allowance reserves the worst case for retries and keeps it for 24 hours after resolution. It is separate from the shared SEC request-rate cap. After the fixed window expires, a reviewed rebase is required.</p>
    {data.reasons.length > 0 && <p className={styles.note}>Recorded constraints: {data.reasons.join(", ")}</p>}
    {data.missedIntervals.length > 0 && <div className={styles.blocker}><h3>Unchecked intervals</h3>{data.missedIntervals.map((range) => <p key={`${range.first}-${range.last}`}>{range.count} slots ({range.first}–{range.last}) were not checked. A later fetch does not establish historical availability.</p>)}</div>}
    {data.slots.map((slot) => <details key={slot.requestId} className={styles.disclosure}>
      <summary>Slot {slot.index} · {slot.outcomeLabel}<span className={styles.captureStatus}>{slot.state}</span></summary>
      <dl className={styles.facts}>
        <div><dt>Nominal cutoff / due (UTC)</dt><dd><Time value={slot.nominalAt} /><br /><Time value={slot.dueAt} /></dd></div>
        <div><dt>Execution / eligible after (UTC)</dt><dd>Attempt {slot.attemptNumber}<br /><Time value={slot.availableAt} /></dd></div>
        <div><dt>Check completed (UTC)</dt><dd><Time value={slot.checkedAt} /></dd></div>
        <div><dt>Filings / new / amendments</dt><dd>{slot.filings ?? "Unknown"} / {slot.newFilings ?? "Unknown"} / {slot.amendments ?? "Unknown"}</dd></div>
        <div><dt>Comparison coverage</dt><dd>Baseline: {slot.coverage?.baseline ?? "Unknown"} · current: {slot.coverage?.current ?? "Unknown"}</dd></div>
        <div><dt>Eligible as next baseline</dt><dd>{slot.eligible ? "Yes · discovery only" : "No"}</dd></div>
        <div><dt>Request / execution</dt><dd><code>{slot.requestId}</code><br /><code>{slot.executionId}</code></dd></div>
        <div><dt>Prior baseline request</dt><dd><code>{slot.baselineRequestId}</code></dd></div>
        <div><dt>Prior manifest / plan SHA256</dt><dd><code>{slot.baselineManifestSha256}</code><br /><code>{slot.planSha256}</code></dd></div>
        <div><dt>Result manifest SHA256</dt><dd><code>{slot.manifestSha256 ?? "No completed result"}</code></dd></div>
      </dl>
    </details>)}
    <details className={styles.disclosure}><summary>Schedule history and retained response evidence</summary>
      <dl className={styles.facts}>
        <div><dt>Schedule / current revision</dt><dd><code>{data.scheduleId}</code><br /><code>{data.revisionId}</code></dd></div>
        <div><dt>Config / saved audit SHA256</dt><dd><code>{data.configSha256}</code><br /><code>{data.auditSha256}</code></dd></div>
      </dl>
      {data.revisions.map((revision) => <div key={revision.epoch} className={styles.monitorAttempt}><h3>Revision {revision.epoch} · {revision.active ? "Active" : "Paused"}</h3><p><Time value={revision.at} /> · {revision.reason}</p><code>{revision.configSha256}</code></div>)}
      {data.attempts.map((attempt) => <div key={attempt.id} className={styles.monitorAttempt}><p>HTTP {attempt.status ?? "not received"} · <code>{attempt.state}</code></p><dl className={styles.facts}>
        <div><dt>Attempt / reused capture</dt><dd><code>{attempt.id}</code><br /><code>{attempt.reusedCaptureId ?? "None"}</code></dd></div>
        <div><dt>Requested / completed (UTC)</dt><dd><Time value={attempt.requestedAt} /><br /><Time value={attempt.finishedAt} /></dd></div>
        <div><dt>Retained body SHA256</dt><dd><code>{attempt.payloadSha256 ?? "No body recorded"}</code><br />{attempt.payloadBytes ?? "Unknown"} bytes</dd></div>
      </dl></div>)}
      <p className={styles.note}>Prior captures and the D4a checkpoint remain unchanged. Unknown crash outcomes are retained; a bounded retry may issue another HTTP request.</p>
    </details>
    <details className={styles.disclosure}><summary>Saved application totals after the scheduled check</summary><dl className={styles.counts}>{data.counts.map((count) => <div key={count.id} data-schedule-count={count.id}><dt>{count.id.replaceAll("_", " ")}</dt><dd>{count.value}</dd></div>)}</dl></details>
    <div className={styles.monitorDisposition}><h3>Automatic financial analysis · not dispatched</h3><p>Quote registration, financial coverage and publication still need their recorded prerequisites. Stock news, CPI/PPI/Fed monitoring and notifications remain separate planned capabilities.</p></div>
  </section>;
}
