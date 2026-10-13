import type { CurrentReviewSnapshot } from "./types";
import styles from "./analysis-readiness.module.css";

export default function CurrentReviewPanel({ data, onInspect }: {
  data: CurrentReviewSnapshot;
  onInspect: (id: string) => void;
}) {
  return <section className={styles.safety} aria-labelledby="current-review-title" data-current-review={data.kind}>
    <div className={styles.sectionHeading}><div><p className="eyebrow">D5e / LATEST CURRENT-WINDOW REVIEW</p><h2 id="current-review-title">Can a new evidence batch proceed?</h2></div><span>Reviewed {data.reviewedOn}</span></div>
    <p>{data.conclusion}</p>
    <div className={styles.decisions}>
      <article data-current-candidate><span className={styles.gateStatus} data-state="blocked">Blocked</span><h3>New PIT batch</h3><p>{data.candidateBatch.explanation}</p><ul>{data.candidateBatch.reasonCodes.map(code => <li key={code}>{code.replaceAll("_", " ")}</li>)}</ul></article>
      <article><h3>Three distinct times</h3><dl>
        <div><dt>Historical September cutoff</dt><dd>{data.historicalRetrievalCutoff}</dd></div>
        <div><dt>Current inventory observed</dt><dd>{data.inventoryObservedAt ?? "Unavailable"}</dd></div>
        <div><dt>All new captures held by</dt><dd>{data.retrievalCutoff ?? "Unavailable"}</dd></div>
      </dl><p>{data.cutoffNote}</p></article>
    </div>
    <div className={styles.gates}>{data.events.map(event => <details key={event.id} data-current-event={event.id}>
      <summary><span>{event.filedDate} · {event.title}</span><span className={styles.gateStatus}>{event.status === "missing" ? "Missing" : "Primary reviewed"}</span></summary>
      <p>{event.finding}</p><p>{event.limit}</p><p>{event.form} · {event.accession} · Items {event.items ?? "Unconfirmed"}</p><p>Body retrieved {event.capturedAt ?? "Unavailable"}</p>
      {data.details[event.id] && <button className={styles.evidenceButton} onClick={() => onInspect(event.id)}>Inspect primary evidence ↗</button>}
    </details>)}</div>
    <details className={styles.safetyDisclosure} data-current-missing><summary>Exact outstanding linked evidence</summary><ul>{data.missingBodies.map(body => <li key={body.resourceKey}><a href={body.url} target="_blank" rel="noreferrer">Exhibit {body.exhibit} · {body.accession} ↗</a><p>{body.reason}</p><span className={styles.accession}>{body.resourceKey}</span></li>)}</ul></details>
    <div className={styles.sectionHeading}><h3>Affected-line and edition reconciliation</h3><span>Reported operands only</span></div>
    <div className={styles.gates}>{data.reconciliation.map(check => <details key={check.id} data-current-check={check.id}>
      <summary><span>{check.label}</span><span className={styles.gateStatus}>{check.status === "unconfirmed" ? "Unconfirmed" : "Prior match"}</span></summary><p>{check.finding}</p><button className={styles.evidenceButton} onClick={() => onInspect(check.detailId)}>Inspect reconciliation evidence ↗</button>
    </details>)}</div>
    {data.details["annual-editions"] && <details className={styles.safetyDisclosure} data-current-annual><summary>Fresh annual Company Facts editions</summary>{data.annualEditionChecks.map(check => <p key={check.concept}>{check.concept}: {check.reason}</p>)}<button className={styles.evidenceButton} onClick={() => onInspect("annual-editions")}>Inspect exact annual source rows ↗</button></details>}
    {data.currentInventory && <details className={styles.safetyDisclosure} data-current-inventory><summary>Current scoped inventory</summary><p>{data.currentInventory.count} primary records · {data.currentInventory.boundaryStart} through {data.currentInventory.boundaryEnd}, as observed at the timestamp above.</p><p>Forms: {data.currentInventory.forms.join(", ")}</p><p>{data.currentInventory.note}</p><a href={data.currentInventory.source.url} target="_blank" rel="noreferrer">Retained inventory source ↗</a></details>}
    <p className={styles.nextStep}>{data.nextStep}</p>
  </section>;
}
