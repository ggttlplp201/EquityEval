import type { RealFundamentalsView } from "./real-types";
import styles from "./analysis-readiness.module.css";

export default function RealFundamentalsPanel({ data, onInspect }: {
  data: RealFundamentalsView; onInspect: (id: string) => void;
}) {
  return <section className={styles.safety} aria-labelledby="real-fundamentals-title" data-real-fundamentals>
    <div className={styles.sectionHeading}>
      <div><p className="eyebrow">D5j / PRESERVED EARLIER PUBLICATION</p><h2 id="real-fundamentals-title">FY2025 reported operating margin</h2></div>
      <span>Descriptive annual result</span>
    </div>
    <div className={styles.metric}>
      <div><p>Operating income ÷ total revenue, including reserve income</p><button className={styles.amount} data-real-margin onClick={() => onInspect("operating_margin")} aria-label="Inspect reported operating-margin evidence"><strong>{data.marginDisplay}</strong><span aria-hidden="true">↗</span></button></div>
      <p>The reported operating loss is preserved. This ratio includes the issuer’s reported expenses; it is not an adjusted or recurring-profit measure. Reserve income and distribution costs shape its meaning.</p>
    </div>
    <div className={styles.decisions}>{data.operands.map(operand => <article key={operand.id}><h3>{operand.label}</h3><button className={styles.evidenceButton} data-real-operand={operand.id} onClick={() => onInspect(operand.id)}>{operand.display} ↗</button><p>Consolidated FY2025 · reported USD · exact context and precision in evidence</p></article>)}</div>
    <div className={styles.decisions}>
      <article><h3>Bounded source knowledge</h3><p>{data.sourceObservation}</p><p>Retrospective source review through this exact observation. It does not establish September application knowledge or coverage after this instant.</p></article>
      <article><h3>Frozen evaluation</h3><p>{data.evaluatedAt}</p><p>Annual historical analysis with the reviewed 365-day freshness policy. This is not a latest-quarter result.</p><button className={styles.evidenceButton} onClick={() => onInspect("policy")}>Inspect policy and safety checks ↗</button></article>
    </div>
    <h3>What remains unavailable</h3>
    <p>In this preserved earlier snapshot, nine metric definitions still require applicability review and source inputs. Accounting identity, quarterly trend and comparison history were unavailable in this snapshot. Price, valuation and sector conclusions remain outside this result.</p>
    <div className={styles.gates}>{data.unresolved.map(metric => <details key={metric.id} data-real-gap={metric.id}><summary><span>{metric.label}</span><span className={styles.gateStatus}>N/A · applicability unresolved</span></summary><p>{metric.requirement}</p></details>)}</div>
    <p className={styles.nextStep}>Published with explicit gaps. No investment recommendation or financial-strength label is implied.</p>
  </section>;
}
