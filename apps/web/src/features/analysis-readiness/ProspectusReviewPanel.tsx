import type { ProspectusReviewSnapshot } from "./types";
import styles from "./analysis-readiness.module.css";

export default function ProspectusReviewPanel({ data, onInspect }: {
  data: ProspectusReviewSnapshot; onInspect: (id: string) => void;
}) {
  return <section className={styles.safety} aria-labelledby="prospectus-review-title" data-prospectus-review>
    <div className={styles.sectionHeading}><div><p className="eyebrow">D5g / LATEST EVIDENCE REVIEW</p><h2 id="prospectus-review-title">Earlier statements match. Registration history remains open.</h2></div><span>Reviewed {data.reviewedOn}</span></div>
    <p>{data.conclusion}</p>
    <div className={styles.decisions}>
      <article data-prospectus-candidate><span className={styles.gateStatus} data-state="blocked">Blocked</span><h3>New PIT batch</h3><p>{data.candidateBatch.explanation}</p><ul>{data.candidateBatch.reasonCodes.map(code => <li key={code}>{code.replaceAll("_", " ")}</li>)}</ul></article>
      <article><h3>Actual evidence times</h3><dl><div><dt>Inventory observed</dt><dd>{data.inventoryObservedAt ?? "Unavailable"}</dd></div><div><dt>Acquired evidence held by</dt><dd>{data.retrievalCutoff ?? "Unavailable"}</dd></div><div><dt>Historical cutoff unchanged</dt><dd>{data.historicalRetrievalCutoff}</dd></div></dl><p>{data.cutoffNote}</p></article>
    </div>
    <div className={styles.gates}>
      {data.comparison && <details data-prospectus-check="statements"><summary><span>IPO statements versus later editions</span><span className={styles.gateStatus}>Tested operands match</span></summary><p>{data.comparison.finding}</p><p>{data.comparison.limit}</p><button className={styles.evidenceButton} onClick={() => onInspect("statements")}>Inspect statements and exact contexts ↗</button></details>}
      <details data-prospectus-check="facts"><summary><span>Every retained Q1 Facts vintage</span><span className={styles.gateStatus}>{data.q1FactsMatch ? "Tested operands match" : "Unconfirmed"}</span></summary><p>Review exact source rows, filing editions, retrieval times and locators. A matching Facts value does not replace a filing-body review.</p><button className={styles.evidenceButton} onClick={() => onInspect("facts")}>Inspect Q1 Facts vintages ↗</button></details>
      <details data-prospectus-check="registration"><summary><span>Unreviewed registration history</span><span className={styles.gateStatus}>Source gap</span></summary><p>The earlier primary roster covered periodic reports and current events. These registration and offering editions need substantive review before claiming complete selected-line history.</p><ul>{data.missingBodies.map(row => <li key={row.resourceKey}><a href={row.url} target="_blank" rel="noreferrer">{row.form} · {row.filedDate} · {row.accession} ↗</a><p>{row.reason}</p></li>)}</ul><button className={styles.evidenceButton} onClick={() => onInspect("registration")}>Inspect exact source requirements ↗</button></details>
      {data.details.annual && <details data-prospectus-check="annual"><summary><span>Fresh FY2025 annual Facts editions</span><span className={styles.gateStatus}>Source rows</span></summary>{data.annualEditionChecks.map(check => <p key={check.concept}>{check.concept}: {check.reason}</p>)}<button className={styles.evidenceButton} onClick={() => onInspect("annual")}>Inspect annual source rows ↗</button></details>}
    </div>
    <p className={styles.nextStep}>{data.nextStep}</p>
  </section>;
}
