import type { ExhibitReviewSnapshot } from "./types";
import styles from "./analysis-readiness.module.css";

export default function ExhibitReviewPanel({ data, onInspect }: {
  data: ExhibitReviewSnapshot;
  onInspect: (id: string) => void;
}) {
  return <section className={styles.safety} aria-labelledby="exhibits-title" data-exhibit-review={data.kind}>
    <div className={styles.sectionHeading}>
      <div><p className="eyebrow">D5d / LATEST EXHIBIT REVIEW</p><h2 id="exhibits-title">What the exhibits establish</h2></div>
      <span>Reviewed {data.reviewedOn}</span>
    </div>
    <p>{data.conclusion}</p>
    <p>{data.reviewedCount} exhibit bodies reviewed within the stated scopes. Historical retrieval cutoff: {data.historicalRetrievalCutoff}.</p>
    <div className={styles.gates}>
      {data.exhibits.map(exhibit => <details key={exhibit.id} data-exhibit={exhibit.id}>
        <summary><span>{exhibit.filedDate} · Exhibit {exhibit.exhibit} · {exhibit.relevance}</span><span className={styles.gateStatus}>{exhibit.status === "missing" ? "Missing" : "Reviewed with limits"}</span></summary>
        <p>{exhibit.finding}</p><p>{exhibit.limit}</p>
        <p>Review scope: {exhibit.scope}</p>
        <p>{exhibit.form} · {exhibit.accession} · Items {exhibit.items}</p>
        <p>Body retrieved {exhibit.capturedAt ?? "N/A"}. Parent filing date is not application knowledge.</p>
        {exhibit.captureId && <button className={styles.evidenceButton} onClick={() => onInspect(exhibit.id)}>Inspect exhibit {exhibit.exhibit} evidence ↗</button>}
        <p><a href={exhibit.url} target="_blank" rel="noreferrer">Open official exhibit ↗</a></p>
      </details>)}
    </div>
    <div className={styles.decisions}>
      <article><span className={styles.gateStatus} data-state="blocked">Blocked</span><h3>Remaining publication gates</h3><ul>{data.blockers.map(blocker => <li key={blocker}>{blocker}</li>)}</ul></article>
      <article><h3>Current inventory is not current clearance</h3>
        {data.freshInventory ? <><p><a href={data.freshInventory.source.url} target="_blank" rel="noreferrer">Retained SEC inventory ↗</a> · retrieved {data.freshInventory.source.capturedAt}</p><ul>{data.freshInventory.outsidePinnedWindow.map(filing => <li key={filing.accession}><a href={filing.url} target="_blank" rel="noreferrer">{filing.form} · {filing.filedDate} · {filing.accession} ↗</a></li>)}</ul><p>These later primary bodies remain outside this exhibit acquisition.</p></> : <p>Fresh inventory unavailable. Capture and review required.</p>}
      </article>
    </div>
    <p className={styles.nextStep}>{data.nextStep}</p>
  </section>;
}
