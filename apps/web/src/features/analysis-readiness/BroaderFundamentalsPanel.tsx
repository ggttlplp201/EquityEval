import type { BroaderFundamentalsView } from "./broader-types";
import styles from "./analysis-readiness.module.css";

export default function BroaderFundamentalsPanel({ data, onInspect }: {
  data: BroaderFundamentalsView; onInspect: (id: string) => void;
}) {
  return <section className={`${styles.safety} ${styles.broader}`} aria-labelledby="broader-title" data-broader-fundamentals>
    <div className={styles.sectionHeading}>
      <div><p className="eyebrow">D5k / PUBLISHED REPORTED FUNDAMENTALS</p><h2 id="broader-title">More reported data, with its accounting limits</h2></div>
      <span>Annual and closing balances kept separate</span>
    </div>
    <p>These are descriptive consolidated results. Reserve income, holder reserve assets and deposit obligations shape their meaning. They do not measure freely available corporate liquidity or imply an investment recommendation.</p>
    <div className={styles.decisions}>
      <article><h3>Bounded source observation</h3><p>{data.sourceObservation}</p><p>This is a retrospective review at the recorded observation, not coverage after that instant or historical September application knowledge.</p></article>
      <article><h3>Expanded evidence review</h3><p>{data.bodyCount} retained filing and exhibit bodies; {data.comparisonCount} matching-period comparisons. No new source acquisition.</p><button className={styles.evidenceButton} data-broader-review onClick={() => onInspect("review")}>Inspect accounting review and exact blockers ↗</button></article>
    </div>
    {data.results.map(result => <section key={result.basis} data-broader-result={result.basis} aria-labelledby={`broader-${result.basis}`}>
      <div className={styles.sectionHeading}><h3 id={`broader-${result.basis}`}>{result.basis === "annual" ? "FY2025 annual results" : "December 31, 2025 closing balances"}</h3><span>Evaluated {result.snapshot.result.selector.evaluated_at}</span></div>
      <div className={styles.decisions}>{result.metrics.map(metric => <article key={metric.id}>
        <h3>{metric.label}</h3><button className={styles.amount} data-broader-metric={metric.metricId} onClick={() => onInspect(metric.id)} aria-label={`Inspect ${metric.label} evidence`}><strong>{metric.display}</strong><span aria-hidden="true">↗</span></button><p>{metric.scope}</p>
      </article>)}</div>
      <p><button className={styles.evidenceButton} data-broader-accounting={result.basis} onClick={() => onInspect(result.accountingDetail)}>Inspect passing closing balance-sheet identity ↗</button></p>
      <details><summary>Exact source operands</summary><div className={styles.decisions}>{result.operands.map(operand => <article key={operand.id}><h4>{operand.label}</h4><button className={styles.evidenceButton} data-broader-operand={operand.id} onClick={() => onInspect(operand.id)}>{operand.display} ↗</button></article>)}</div></details>
      <details><summary>Explicit gaps in this result</summary><p>Metrics belonging to the companion period remain null here. Gross margins, growth and ROA still need the exact reviews listed below.</p><div className={styles.gates}>{result.gaps.map(gap => <details key={gap.id} data-broader-gap={`${result.basis}:${gap.id}`}><summary><span>{gap.label}</span><span className={styles.gateStatus}>N/A · unsupported in this result</span></summary><p>{gap.requirement}</p></details>)}</div></details>
    </section>)}
    <h3>Comparative source rows are not complete analysis history</h3>
    <p>{data.findings.history} Growth needs an eligible earlier revenue period; ROA needs an eligible opening asset balance. Retained comparative numbers alone do not clear those gates.</p>
    <details><summary>Inspect earlier annual comparative rows</summary><div className={styles.decisions}>{data.comparativeRows.map(row => <article key={row.id}><h4>{row.label}</h4><p>{row.period}</p><button className={styles.evidenceButton} data-broader-comparative={row.id} onClick={() => onInspect(row.id)}>{row.display} ↗</button><p>Source comparison only · not analysis eligible</p></article>)}</div></details>
    <details><summary>Exact missing earlier-history bodies</summary><ul>{data.missingHistory.map(item => <li key={item.resourceKey}><strong>{item.form} · {item.filedDate}</strong><p>{item.resourceKey}</p><p>{item.reason}. {item.acquisitionContract}.</p></li>)}</ul></details>
    <p className={styles.nextStep}>Earlier registration history needs a separately reviewed acquisition boundary, including the unsupported PDF resources. Quarterly trends, full comparison history, prices, valuation and sector conclusions remain unavailable.</p>
  </section>;
}
