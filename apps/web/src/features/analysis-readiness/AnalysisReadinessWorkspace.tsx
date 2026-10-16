"use client";

import Link from "next/link";
import { useState } from "react";
import EvidenceDrawer from "@/components/EvidenceDrawer";
import WorkbenchShell from "@/components/WorkbenchShell";
import BroaderFundamentalsPanel from "./BroaderFundamentalsPanel";
import type { BroaderFundamentalsView } from "./broader-types";
import RealFundamentalsPanel from "./RealFundamentalsPanel";
import type { RealFundamentalsView } from "./real-types";
import ObservationReviewPanel from "./ObservationReviewPanel";
import RegistrationReviewPanel from "./RegistrationReviewPanel";
import ProspectusReviewPanel from "./ProspectusReviewPanel";
import LeadershipReviewPanel from "./LeadershipReviewPanel";
import CurrentReviewPanel from "./CurrentReviewPanel";
import ExhibitReviewPanel from "./ExhibitReviewPanel";
import SafetyReviewPanel from "./SafetyReviewPanel";
import type { AnalysisReadinessSnapshot, SafetyReviewSnapshot, ExhibitReviewSnapshot, CurrentReviewSnapshot, LeadershipReviewSnapshot, ProspectusReviewSnapshot, RegistrationReviewSnapshot, ObservationReviewSnapshot } from "./types";
import styles from "./analysis-readiness.module.css";

const statusLabels = {
  blocked: "Blocked",
  not_reviewed: "Not reviewed",
  not_implemented: "Not implemented",
} as const;

export default function AnalysisReadinessWorkspace({ broader, real, data, safety, exhibits, current, leadership, prospectus, registration, observation }: { broader: BroaderFundamentalsView; real: RealFundamentalsView; data: AnalysisReadinessSnapshot; safety: SafetyReviewSnapshot; exhibits: ExhibitReviewSnapshot; current: CurrentReviewSnapshot; leadership: LeadershipReviewSnapshot; prospectus: ProspectusReviewSnapshot; registration: RegistrationReviewSnapshot; observation: ObservationReviewSnapshot }) {
  const [detailId, setDetailId] = useState<string | null>(null);
  return <WorkbenchShell active="pilot">
    <main id="main-content" tabIndex={-1} className={styles.page} data-analysis-readiness-kind={data.kind}>
      <Link href="/development/pilot/pipeline" className={styles.back}>← Application pipeline</Link>
      <header className={styles.header}>
        <div>
          <p className="eyebrow">{data.company.ticker} / REAL ANALYSIS READINESS</p>
          <h1>Analysis gate<span aria-hidden="true">.</span></h1>
          <p>FY2025 annual and closing balances · two published results with explicit gaps</p>
        </div>
        <div className={styles.stamp} data-state={data.status}>
          <strong>PUBLISHED WITH GAPS</strong>
          <span>10 normalized source concepts</span>
          <span>6 supported definitions · annual 4 / closing 2</span>
          <span>Observed {broader.sourceObservation.slice(0, 10)}</span>
          <span>Published {broader.results[0].snapshot.generated_at.slice(0, 10)}</span>
        </div>
      </header>

      <section className={styles.boundary} aria-labelledby="readiness-boundary-title">
        <p className="eyebrow">PUBLICATION BOUNDARY</p>
        <h2 id="readiness-boundary-title">Six reported metric definitions are available.</h2>
        <p>Separate annual and closing-balance results appear first. The annual result has four supported metrics and six explicit gaps; the closing result has two supported metrics and eight explicit gaps. Other-period metrics remain null in each result. Saved September selections keep their original incomplete-history flags.</p>
      </section>

      <BroaderFundamentalsPanel data={broader} onInspect={(id) => setDetailId(`broader:${id}`)} />
      <RealFundamentalsPanel data={real} onInspect={(id) => setDetailId(`real:${id}`)} />
      <p className={styles.nextStep}>Archived checkpoints below retain the decisions and publication boundaries that applied at the time.</p>
      <ObservationReviewPanel data={observation} onInspect={(id) => setDetailId(`observation:${id}`)} />
      <RegistrationReviewPanel data={registration} onInspect={(id) => setDetailId(`registration:${id}`)} />
      <ProspectusReviewPanel data={prospectus} onInspect={(id) => setDetailId(`prospectus:${id}`)} />
      <LeadershipReviewPanel data={leadership} onInspect={(id) => setDetailId(`leadership:${id}`)} />

      <CurrentReviewPanel data={current} onInspect={(id) => setDetailId(`current:${id}`)} />

      <ExhibitReviewPanel data={exhibits} onInspect={(id) => setDetailId(`exhibits:${id}`)} />

      <SafetyReviewPanel data={safety} onInspect={(id) => setDetailId(`safety:${id}`)} />

      <section aria-labelledby="inputs-title">
        <div className={styles.sectionHeading}>
          <div><p className="eyebrow">SAVED D5a INPUTS</p><h2 id="inputs-title">Historical normalized inputs</h2></div>
          <Link href={data.source.normalizationHref}>Inspect source evidence ↗</Link>
        </div>
        <div className={styles.inputs}>
          {data.inputs.map((input) => <article key={input.id} data-analysis-input={input.id}>
            <span className={styles.available}>Normalized</span>
            <h3>{input.label}</h3>
            <button className={styles.amount} onClick={() => setDetailId(input.detailId)} aria-label={`Inspect ${input.label} evidence`}>
              <strong>{input.displayValue}</strong><span aria-hidden="true">↗</span>
            </button>
            <p>{data.periodLabel} · abbreviated display · exact amount in evidence</p>
            <div className={styles.unusable}><span aria-hidden="true">×</span> Unavailable for analysis</div>
          </article>)}
        </div>
      </section>

      <section className={styles.metric} aria-labelledby="candidate-metric-title">
        <div>
          <p className="eyebrow">HISTORICAL D5a CANDIDATE</p>
          <h2 id="candidate-metric-title">{data.candidateMetric.label}</h2>
          <code>{data.candidateMetric.formula}</code>
        </div>
        <div className={styles.metricResult}>
          <strong>{data.candidateMetric.displayValue}</strong>
          <span>Blocked</span>
        </div>
        <p className={styles.metricNote}>No ratio was published from this September checkpoint. Having both numeric amounts does not override its historical point-in-time quality flags.</p>
      </section>

      <section aria-labelledby="gates-title">
        <div className={styles.sectionHeading}>
          <div><p className="eyebrow">ORIGINAL SAVED D5b GATES</p><h2 id="gates-title">Original publication decision</h2></div>
          <span>{data.gates.length} checks</span>
        </div>
        <div className={styles.gates}>
          {data.gates.map((gate) => <details key={gate.id} data-readiness-gate={gate.id}>
            <summary><span>{gate.label}</span><span className={styles.gateStatus} data-state={gate.status}>{statusLabels[gate.status]}</span></summary>
            <p>{gate.reason}</p>
          </details>)}
        </div>
      </section>

      <aside className={styles.meaning} aria-labelledby="meaning-title">
        <h2 id="meaning-title">How to read this page</h2>
        <p>This is a readiness decision, not an investment judgment. “Blocked” means the evidence contract is incomplete. It does not mean CRCL is financially weak, overvalued, or unattractive.</p>
      </aside>

      <footer className={styles.footer}>
        <span>READ-ONLY · HISTORICAL D5a BATCH {data.batchId.slice(0, 8)}</span>
        <div><Link href={data.source.normalizationHref}>Normalized financials ↗</Link><Link href="/help#real-normalization">User guide ↗</Link></div>
      </footer>
    </main>
    <EvidenceDrawer detail={detailId?.startsWith("broader:") ? broader.details[detailId.slice(8)] : detailId?.startsWith("real:") ? real.details[detailId.slice(5)] : detailId?.startsWith("observation:") ? observation.details[detailId.slice(12)] : detailId?.startsWith("registration:") ? registration.details[detailId.slice(13)] : detailId?.startsWith("prospectus:") ? prospectus.details[detailId.slice(11)] : detailId?.startsWith("leadership:") ? leadership.details[detailId.slice(11)] : detailId?.startsWith("current:") ? current.details[detailId.slice(8)] : detailId?.startsWith("exhibits:") ? exhibits.details[detailId.slice(9)] : detailId?.startsWith("safety:") ? safety.details[detailId.slice(7)] : detailId ? data.details[detailId] : undefined} onClose={() => setDetailId(null)} eyebrow="REAL APPLICATION / CRCL" />
  </WorkbenchShell>;
}
