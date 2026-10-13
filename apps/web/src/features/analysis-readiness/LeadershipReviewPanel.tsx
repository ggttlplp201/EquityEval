import type { LeadershipReviewSnapshot } from "./types";
import styles from "./analysis-readiness.module.css";

export default function LeadershipReviewPanel({ data, onInspect }: {
  data: LeadershipReviewSnapshot; onInspect: (id: string) => void;
}) {
  return <section className={styles.safety} aria-labelledby="leadership-review-title" data-leadership-review>
    <div className={styles.sectionHeading}><div><p className="eyebrow">D5f / SAVED LEADERSHIP REVIEW</p><h2 id="leadership-review-title">One exhibit gap closed. Accounting scope remains open.</h2></div><span>Reviewed {data.reviewedOn}</span></div>
    <p>Saved D5f decision. The D5g review above records the subsequently acquired IPO prospectus and exact remaining registration-history gap.</p><p>{data.conclusion}</p>
    <div className={styles.decisions}>
      <article data-leadership-candidate><span className={styles.gateStatus} data-state="blocked">Blocked</span><h3>New PIT batch</h3><p>{data.candidateBatch.explanation}</p><ul>{data.candidateBatch.reasonCodes.map(code => <li key={code}>{code.replaceAll("_", " ")}</li>)}</ul></article>
      <article><h3>Actual evidence times</h3><dl><div><dt>Inventory observed</dt><dd>{data.inventoryObservedAt ?? "Unavailable"}</dd></div><div><dt>Acquired evidence held by</dt><dd>{data.retrievalCutoff ?? "Unavailable"}</dd></div><div><dt>Historical cutoff unchanged</dt><dd>{data.historicalRetrievalCutoff}</dd></div></dl><p>{data.cutoffNote}</p></article>
    </div>
    <div className={styles.gates}>
      <details data-leadership-check="leadership"><summary><span>CFO-transition Exhibit 99.1</span><span className={styles.gateStatus}>{data.event.status}</span></summary><p>{data.event.finding}</p><p>Retrieved {data.event.capturedAt ?? "Unavailable"}</p>{data.details.leadership && <button className={styles.evidenceButton} onClick={() => onInspect("leadership")}>Inspect full-body review ↗</button>}</details>
      <details data-leadership-check="accounting"><summary><span>Retained accounting evidence</span><span className={styles.gateStatus}>Unconfirmed scope</span></summary><p>{data.accounting.finding}</p><p>{data.accounting.limit}</p><button className={styles.evidenceButton} onClick={() => onInspect("accounting")}>Inspect every retained periodic body ↗</button></details>
      <details data-leadership-check="prospectus"><summary><span>Exact earlier-edition source candidate</span><span className={styles.gateStatus}>Body unreviewed</span></summary><p>The retained inventory identifies this IPO prospectus. Its Q1 content and sufficiency remain unconfirmed.</p><a href={data.nextSourceUrl} target="_blank" rel="noreferrer">Open SEC prospectus ↗</a><p className={styles.accession}>{data.nextSource}</p><button className={styles.evidenceButton} onClick={() => onInspect("prospectus")}>Inspect retained inventory metadata ↗</button></details>
      <details data-leadership-check="q1-facts"><summary><span>Earlier Q1 Company Facts editions</span><span className={styles.gateStatus}>Source attribution</span></summary><p>Inspect every retained governed Facts vintage and its exact Q1 row locators. Filing attribution does not replace an earlier primary-body review.</p><button className={styles.evidenceButton} onClick={() => onInspect("q1-facts")}>Inspect Q1 Facts vintages ↗</button></details>
      {data.details.annual && <details data-leadership-check="annual"><summary><span>Fresh annual edition checks</span><span className={styles.gateStatus}>Source rows</span></summary>{data.annualEditionChecks.map(check => <p key={check.concept}>{check.concept}: {check.reason}</p>)}<button className={styles.evidenceButton} onClick={() => onInspect("annual")}>Inspect annual source rows ↗</button></details>}
    </div>
    {data.currentInventory && <details className={styles.safetyDisclosure}><summary>Fresh scoped inventory · {data.currentInventory.status.replaceAll("_", " ")}</summary><p>{data.currentInventory.count} scoped primary identities. {data.currentInventory.note}</p><a href={data.currentInventory.source.url} target="_blank" rel="noreferrer">SEC inventory source ↗</a></details>}
    <p className={styles.nextStep}>{data.nextStep}</p>
  </section>;
}
