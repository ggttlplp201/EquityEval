import type { ObservationReviewSnapshot } from "./types";
import styles from "./analysis-readiness.module.css";

export default function ObservationReviewPanel({ data, onInspect }: {
  data: ObservationReviewSnapshot; onInspect: (id: string) => void;
}) {
  return <section className={styles.safety} aria-labelledby="observation-review-title" data-observation-review>
    <div className={styles.sectionHeading}><div><p className="eyebrow">D5i / LATEST SOURCE REVIEW</p><h2 id="observation-review-title">Current source coverage verified. Real analysis publication is separate.</h2></div><span>Reviewed {data.reviewedOn}</span></div>
    <div className={styles.decisions}>
      <article data-observation-candidate><span className={styles.gateStatus}>{data.normalizationStatus === "published" ? "Published normalization" : "Prepared; publication review pending"}</span><h3>Current source batch</h3><p>{data.batchId ?? "No new batch published yet"}</p><p>The selected annual source operands pass the reviewed history and accounting checks. This is a normalization result, not an operating-margin or valuation result.</p></article>
      <article><h3>Exact current observation</h3><p>{data.capturedBefore}</p><p>{data.timeScope.interpretation}</p><p>{data.metadataNote}</p></article>
    </div>
    <div className={styles.gates}>
      <details data-observation-check="observation"><summary><span>Fresh inventory, editions and metadata vintages</span><span className={styles.gateStatus}>Reviewed</span></summary><p>Inspect the exact scoped roster, financial edition checks, retained source times and historical metadata differences.</p><button className={styles.evidenceButton} onClick={() => onInspect("observation")}>Inspect observation and provenance ↗</button></details>
    </div>
    <div className={styles.decisions}>{data.facts.map(fact => <article key={fact.id}><h3>{fact.label}</h3><button className={styles.evidenceButton} data-observation-fact={fact.id} onClick={() => onInspect(fact.id)}>{fact.value} {fact.unit} ↗</button><p>FY2025 consolidated reported source amount; open for exact filing context and transform.</p></article>)}</div>
    <p className={styles.nextStep}>{data.publicationBlocker}</p><p>Operating margin: N/A. Published financial metrics: {data.publishedMetricCount}.</p>
  </section>;
}
