import type { SafetyReviewSnapshot } from "./types";
import styles from "./analysis-readiness.module.css";

const bodyLabels = {
  retained_at_cutoff: "Retained by September cutoff",
  retrospective_only: "Retrieved later · retrospective evidence only",
  missing: "Body missing",
} as const;

export default function SafetyReviewPanel({ data, onInspect }: {
  data: SafetyReviewSnapshot;
  onInspect: (id: string) => void;
}) {
  return <section className={styles.safety} aria-labelledby="safety-title" data-safety-review={data.kind}>
    <div className={styles.sectionHeading}>
      <div><p className="eyebrow">D5c / EVIDENCE REVIEW</p><h2 id="safety-title">What the safety checks establish</h2></div>
      <span>Reviewed {data.reviewedOn}</span>
    </div>
    <div className={styles.decisions}>
      <article data-safety-decision="historical">
        <span className={styles.gateStatus} data-state="blocked">Blocked</span>
        <h3>Historical application knowledge</h3>
        <p>{data.historicalDecision.explanation}</p>
        <p>Retrieval cutoff: <time>{data.historicalRetrievalCutoff}</time></p>
      </article>
      <article data-safety-decision="retrospective">
        <span className={styles.gateStatus}>Incomplete</span>
        <h3>Retrospective content review</h3>
        <p>{data.retrospectiveDecision.explanation}</p>
        <p>{data.acquisition.note}</p>
      </article>
    </div>
    <div className={styles.gates}>
      {data.checks.map(check => <details key={check.id} data-safety-check={check.id}>
        <summary><span>{check.label}</span><span className={styles.gateStatus} data-state={check.status}>{check.status}</span></summary>
        <p>{check.explanation}</p>
        <button className={styles.evidenceButton} onClick={() => onInspect(check.detailId)}>Inspect {check.label} evidence ↗</button>
      </details>)}
    </div>
    <details className={styles.safetyDisclosure} data-safety-profile>
      <summary>CRCL business and metric profile</summary>
      <h3>{data.profile.business_model}</h3>
      <p>Known and effective from {data.profile.known_on}. Descriptive operating-margin interpretation only; this does not activate S5 publication.</p>
      <ul>{data.profileNotes.map(note => <li key={note}>{note}</li>)}</ul>
      <button className={styles.evidenceButton} onClick={() => onInspect("profile")}>Inspect profile sources ↗</button>
    </details>
    <details className={styles.safetyDisclosure} data-safety-coverage>
      <summary>Filing coverage and review status</summary>
      <p>Financial period: {data.period}. Filing window: {data.inventoryWindow}.</p>
      <p><a href={data.inventorySource.url} target="_blank" rel="noreferrer">SEC inventory metadata ↗</a> · captured {data.inventorySource.capturedAt}. A retained body is not a completed content review.</p>
      {data.filings.map(filing => <details key={filing.accession} className={styles.filing} data-safety-filing={filing.accession}>
        <summary><span>{filing.form} · {filing.filedDate}</span><span>{filing.accession}</span></summary>
        <p>{bodyLabels[filing.bodyStatus]}</p>
        <p>{filing.reviewSummary}</p>
        <dl>
          <div><dt>Body captured</dt><dd>{filing.completedAt ?? "N/A"}</dd></div>
          <div><dt>Accepted</dt><dd>{filing.acceptedAt}</dd></div>
          <div><dt>Reported period end</dt><dd>{filing.reportPeriodEnd ?? "N/A"}</dd></div>
          <div><dt>Event items</dt><dd>{filing.items || "N/A"}</dd></div>
          <div><dt>Capture</dt><dd>{filing.captureId ?? "N/A"}</dd></div>
          <div><dt>Body SHA256</dt><dd>{filing.bodySha256 ?? "N/A"}</dd></div>
          <div><dt>Inventory locator</dt><dd>{filing.metadataLocator} · {filing.metadataCaptureId}</dd></div>
        </dl>
        <a href={filing.url} target="_blank" rel="noreferrer">Open official filing ↗</a>
      </details>)}
    </details>
    <details className={styles.safetyDisclosure} data-safety-missing>
      <summary>Exact outstanding exhibits and later filings</summary>
      <p>These exhibit links were identified in the reviewed primary filings. Their bodies have not been retained or reviewed for this decision.</p>
      <ul>{data.missingExhibits.map(exhibit => <li key={exhibit.url} data-missing-exhibit>
        <a href={exhibit.url} target="_blank" rel="noreferrer">{exhibit.label} ↗</a><span className={styles.accession}>{exhibit.accession}</span>
      </li>)}</ul>
      <h3>Later events outside the pinned window</h3>
      <p>Fresh inventory captured {data.freshInventory.source.capturedAt} identifies these later filings. They require review before any current-cutoff eligibility claim.</p>
      <ul>{data.freshInventory.outsidePinnedWindow.map(filing => <li key={filing.accession} data-later-filing>
        <a href={filing.url} target="_blank" rel="noreferrer">{filing.form} · {filing.filedDate} · {filing.accession} ↗</a>
      </li>)}</ul>
    </details>
    <p className={styles.nextStep}>{data.nextStep}</p>
  </section>;
}
