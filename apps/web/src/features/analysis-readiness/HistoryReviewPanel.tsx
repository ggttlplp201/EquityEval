import type { HistoryReviewView } from "./history-types";
import styles from "./analysis-readiness.module.css";

const blockerLabels: Record<string, string> = {
  ars_body_limit: "Annual-report body missing after download limit",
  pdf_limits_unavailable: "Bounded PDF review runtime unavailable",
  post_body_pair_not_captured: "Final Facts and Submissions observation missing",
  affected_line_edition_reconciliation_unresolved: "Accounting editions still need reconciliation",
  gross_margin_applicability_and_operands_unreviewed: "Gross-margin inputs and business applicability unreviewed",
  historical_periods_and_trend_contract_inputs_unreviewed: "Comparable history and trend samples unreviewed",
};
const metricLabels: Record<string, string> = { gross_margin: "Gross margin", revenue_growth: "Revenue growth", return_on_assets: "Return on assets", history_trend: "History and trends" };

export default function HistoryReviewPanel({ data, onInspect }: { data: HistoryReviewView; onInspect: (id: string) => void }) {
  return <section className={styles.safety} aria-labelledby="history-review-title" data-history-review={data.kind}>
    <div className={styles.sectionHeading}><div><p className="eyebrow">D5l / HISTORY EVIDENCE CHECKPOINT</p><h2 id="history-review-title">What still blocks broader history?</h2></div><span>Blocked</span></div>
    <p>{data.retainedBodyCount} of 47 documents retained: 39 HTML and seven PDFs. The annual-report PDF exceeded the reviewed download limit. All seven retained PDFs remain blocked from content review by the required memory-limit check.</p>
    <p>{data.reviewLimit}</p>
    <div className={styles.decisions}>
      <article><h3>Acquisition and knowledge cutoff</h3><dl><div><dt>Run completed</dt><dd>{data.acquisitionCompletedAt}</dd></div><div><dt>Fixed filing window ends</dt><dd>{data.filingDateScopeEnd}</dd></div><div><dt>Final post-body pair</dt><dd>Not captured</dd></div></dl><p>{data.cutoffNote}</p></article>
      <article><h3>No new financial publication</h3><p>The six previously published definitions below retain their original evidence and dates. This incomplete acquisition does not replace those snapshots or establish additional eligible periods.</p><ul>{data.blockers.map(reason => <li key={reason}>{blockerLabels[reason] ?? reason}</li>)}</ul></article>
    </div>
    <div className={styles.gates}>{data.metrics.map(metric => <details key={metric.id} data-history-metric={metric.id}><summary><span>{metricLabels[metric.id] ?? metric.id}</span><span className={styles.gateStatus}>N/A</span></summary><p>{metric.reason}</p></details>)}</div>
    <details className={styles.safetyDisclosure} data-history-roster><summary>Inspect the exact 47-document roster</summary><div className={styles.gates}>{data.bodies.map(body => <details key={body.accession} data-history-body={body.accession}><summary><span>{body.filedDate} · {body.form}</span><span className={styles.gateStatus}>{body.retained ? body.actualContentType === "application/pdf" ? "PDF review blocked" : "Retained · not cleared" : "Body missing"}</span></summary><p>{body.finding}</p><p className={styles.accession}>{body.accession}</p><button className={styles.evidenceButton} onClick={() => onInspect(body.accession)}>Inspect retained evidence and limits ↗</button></details>)}</div></details>
    <p className={styles.nextStep}>{data.nextStep}</p>
  </section>;
}
