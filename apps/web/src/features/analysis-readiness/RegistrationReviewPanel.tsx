import type { RegistrationReviewSnapshot } from "./types";
import styles from "./analysis-readiness.module.css";

export default function RegistrationReviewPanel({ data, onInspect }: {
  data: RegistrationReviewSnapshot; onInspect: (id: string) => void;
}) {
  return <section className={styles.safety} aria-labelledby="registration-review-title" data-registration-review>
    <div className={styles.sectionHeading}><div><p className="eyebrow">D5h / LATEST EVIDENCE REVIEW</p><h2 id="registration-review-title">Statements reconcile. Current coverage remains blocked.</h2></div><span>Reviewed {data.reviewedOn}</span></div>
    <p>{data.conclusion}</p>
    <div className={styles.decisions}>
      <article data-registration-candidate><span className={styles.gateStatus} data-state="blocked">Blocked</span><h3>New PIT batch</h3><p>{data.candidateBatch.explanation}</p><ul>{data.candidateBatch.reasonCodes.map(code => <li key={code}>{code.replaceAll("_", " ")}</li>)}</ul><p>No eligible preparation or new publication. The historical batch retains its original flags; operating margin remains N/A.</p></article>
      <article><h3>Observation is not full-day coverage</h3><dl><div><dt>Inventory observed</dt><dd>{data.inventoryObservedAt ?? "Unavailable"}</dd></div><div><dt>Final body retained</dt><dd>{data.retrievalCutoff ?? "Unavailable"}</dd></div><div><dt>Historical cutoff unchanged</dt><dd>{data.historicalRetrievalCutoff}</dd></div></dl><p>The inventory observation precedes the final retained body. A shared calendar date cannot prove coverage of that later instant or the whole day.</p><p>{data.cutoffNote}</p></article>
    </div>
    <div className={styles.gates}>
      {data.documents.map(row => <details key={row.accession} data-registration-check={row.accession}><summary><span>{row.form} · {row.filedDate}</span><span className={styles.gateStatus}>Reviewed body</span></summary><p>{row.finding}</p><p>{row.limit}</p><button className={styles.evidenceButton} onClick={() => onInspect(row.accession)}>Inspect statements and accounting passages ↗</button></details>)}
      <details data-registration-check="comparisons"><summary><span>Periodic statements and all retained Facts vintages</span><span className={styles.gateStatus}>Selected operands match</span></summary><p>Exact reported periods, contexts, editions, units, scales and signs are compared. Preliminary blank tables, pro forma results and arithmetic-derived quarters are excluded. Matching selected lines is not certification of every accounting line or external assurance report.</p><button className={styles.evidenceButton} onClick={() => onInspect("comparisons")}>Inspect comparisons and source lineage ↗</button></details>
    </div>
    <p>{data.acquisitionAssessment.note}</p><p className={styles.nextStep}>{data.nextStep}</p>
  </section>;
}
