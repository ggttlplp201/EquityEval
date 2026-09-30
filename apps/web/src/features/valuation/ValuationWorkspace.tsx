"use client";

import Link from "next/link";
import { useState } from "react";
import type { Evaluation, SolveResult } from "@equity/schema/types/valuation";
import WorkbenchShell from "@/components/WorkbenchShell";
import EvidenceDrawer from "@/components/EvidenceDrawer";
import type { EvidenceDetail } from "@/features/sectors/types";
import type { Example } from "./types";
import { exact, interval, number, states, words } from "./presentation";
import styles from "./valuation.module.css";

function SolverEvidence({ solve }: { solve: SolveResult }) {
  return <details className={styles.disclosure}><summary>Numerical evidence · exact intervals</summary>
    <p>Root intervals describe numerical precision. They are separate from scenario dispersion and source measurement uncertainty.</p>
    <dl><dt>Root intervals</dt><dd>{exact(solve.root_intervals)}</dd><dt>Unresolved domains</dt><dd>{exact(solve.unresolved_domains)}</dd><dt>Residual interval</dt><dd>{exact(solve.residual)}</dd><dt>Evaluations / subdivisions / iterations</dt><dd>{solve.evaluations} / {solve.subdivisions} / {solve.iterations}</dd><dt>Proof revision</dt><dd>{solve.proof_revision}</dd><dt>Domain certificates</dt><dd>{exact(solve.proof)}</dd></dl>
  </details>;
}
function Terminal({ evaluation }: { evaluation: Evaluation | null }) {
  return <div className={styles.terminal}><span>Terminal contribution / operating EV</span><strong>{number(evaluation?.terminal_contribution, true)}</strong><span>{evaluation?.terminal_dominant === true ? "Terminal dominant · above 75%" : evaluation?.terminal_dominant === false ? "At or below 75%" : "N/A"}</span></div>;
}
export default function ValuationWorkspace({ example, choices }: {
  example: Example; choices: Pick<Example, "id" | "label">[];
}) {
  const [pending, setPending] = useState(false);
  const [scenarioIndex, setScenarioIndex] = useState(0);
  const [gridIndex, setGridIndex] = useState(0);
  const [cellIndex, setCellIndex] = useState(0);
  const [tab, setTab] = useState("reverse");
  const [detail, setDetail] = useState<EvidenceDetail>();
  const payload = example.payload;
  const scenario = payload?.scenarios[scenarioIndex];
  const assumption = payload?.assumptions.scenarios[scenarioIndex];
  const grid = payload?.sensitivities[gridIndex];
  const cell = grid?.cells[cellIndex];
  function inspect(title: string, value: unknown) {
    if (!payload) return;
    setDetail({ title, subtitle: "Fictional frozen inputs · USD amounts; rates are fractions in exact evidence.",
      sections: [
        { heading: "Selected evidence", rows: [{ label: title, value: exact(value) }] },
        { heading: "Model and assumption identity", rows: [{ label: "Model", value: exact(payload.model) }, { label: "Policy", value: exact(payload.policy) }, { label: "Assumptions", value: exact(payload.assumptions) }] },
        { heading: "Source lineage", rows: [{ label: "Valuation date", value: payload.valuation_at }, { label: "Source snapshot", value: payload.source_snapshot_id }, { label: "Payload hash", value: payload.source_payload_hash }, { label: "Input hash", value: payload.source_input_hash }, { label: "Dependency hash", value: payload.dependency_hash }, { label: "Selection and financial period", value: exact(payload.source_selector) }, { label: "Quote selection", value: exact(payload.price) }, { label: "Share pool", value: exact(payload.shares) }, { label: "Claims and exclusions", value: exact(payload.claims) }] },
      ], sources: [{ label: "Synthetic presentation manifest", capturedAt: payload.bridge_captured_before, transform: "Validated S7a manifest → equity_core.valuation_payload.calculate_payload → checked JSON → display formatting", licence: "Fictional development evidence; source IDs and hashes are illustrative" }],
    });
  }
  const valueButton = (title: string, raw: string | null | undefined, percent = false, evidence: unknown = raw) => <button className={styles.value} onClick={() => inspect(title, evidence)} aria-label={`${title}: ${number(raw, percent)}. Inspect evidence`}>{number(raw, percent)} <span aria-hidden="true">↗</span></button>;
  return <WorkbenchShell active="valuation" fictional><main id="main-content" tabIndex={-1} className={styles.page}>
    <header className={styles.heading}><div><p className="eyebrow">VALUATION / FICTIONAL WORKED EXAMPLE</p><h1>What must the model imply?</h1><p>Reverse DCF · operating FCFF · read-only</p></div><Link href="/help#valuation">How to read this view ↗</Link></header>
    <div className={styles.context}><label>Fictional example<select aria-label="Fictional example" value={example.id} disabled={pending} onChange={(event) => { setPending(true); window.location.assign(`/development/valuation?example=${encodeURIComponent(event.target.value)}`); }}>{choices.map((choice) => <option key={choice.id} value={choice.id}>{choice.label}</option>)}</select></label><div><span>Valuation date</span><strong>{payload?.valuation_at ?? "N/A"}</strong></div><div><span>Freshness</span><strong>Frozen fictional snapshot</strong><small>Quote: {payload?.price.reference_date ?? "N/A"} · assumptions: {payload?.assumptions.authored_at ?? "N/A"}</small></div></div>
    <p role="status" className={styles.status}>{pending ? "Loading example…" : `${example.label}${scenario ? ` · ${scenario.name} · ${states[scenario.solve.state]}` : " · Missing"}`}</p>
    {!payload ? <section className={styles.panel}><h2>Missing saved result</h2><p>N/A</p></section> : <>
      <section className={styles.metrics} aria-label="Observed inputs and target">
        <div><span>Observed market common value · {payload.currency}</span>{valueButton("Observed market common value", payload.bridge.market_common_value, false, { price: payload.price, shares: payload.shares, bridge: payload.bridge })}</div>
        <div><span>Operating EV target · {payload.currency}</span>{valueButton("Operating EV target", payload.bridge.market_ev_target, false, payload.bridge)}</div>
        <div><span>Deterministic scenario span</span><button className={styles.value} onClick={() => inspect("Scenario dispersion", { span: payload.scenario_dispersion, scenarios: payload.scenarios })}>{interval(payload.scenario_dispersion, true)} ↗</button><small>Complete eligible named roster · {scenario ? words(scenario.solve_variable) : "N/A"}</small></div>
      </section>
      <div className="segmented" aria-label="Valuation view">{[["reverse", "Reverse DCF"], ["sensitivity", "Sensitivity"]].map(([id, label]) => <button key={id} aria-pressed={tab === id} onClick={() => setTab(id)}>{label}</button>)}</div>
      {tab === "reverse" && scenario && assumption ? <section className={styles.panel} aria-label="Reverse DCF">
        <div className={styles.sectionHeading}><h2>Named scenarios</h2><label>Scenario<select aria-label="Scenario" value={scenarioIndex} onChange={(event) => setScenarioIndex(Number(event.target.value))}>{payload.scenarios.map((row, index) => <option key={row.name} value={index}>{row.name}</option>)}</select></label></div>
        <div className={styles.result}><div><span>Conditional implied {words(scenario.solve_variable)}</span>{valueButton("Implied parameter", scenario.solve.representative, true, scenario)}<strong data-solve-state={scenario.solve.state}>{states[scenario.solve.state]}</strong></div><div><span>Declared search domain</span><strong>{interval(assumption.solve, true)}</strong><small>{scenario.solve.reasons.map(words).join(" · ") || "Complete domain certified"}</small></div></div>
        <Terminal evaluation={scenario.evaluation} />
        <p className={styles.status}>{scenario.reasons.map(words).join(" · ")}</p>
        <div className={styles.tableWrap}><table><caption>Scenario roster · rates are fractions; exact core values</caption><thead><tr><th>Scenario</th><th>Variable</th><th>Domain</th><th>State</th><th>Exact result</th></tr></thead><tbody>{payload.scenarios.map((row, index) => <tr key={row.name}><th><button className="text-button" onClick={() => setScenarioIndex(index)}>{row.name}</button></th><td>{words(row.solve_variable)}</td><td>{exact(payload.assumptions.scenarios[index].solve.lower)} – {exact(payload.assumptions.scenarios[index].solve.upper)}</td><td>{states[row.solve.state]}</td><td><button className="text-button" onClick={() => inspect(row.name, row)}>{exact(row.solve.representative)}</button></td></tr>)}</tbody></table></div>
        <SolverEvidence solve={scenario.solve} />
        <details className={styles.disclosure}><summary>Forecast and terminal amounts · exact {payload.currency}</summary>{scenario.evaluation ? <><div className={styles.tableWrap}><table><thead><tr><th>Year</th><th>Revenue</th><th>EBIT</th><th>Cash tax</th><th>NOPAT</th><th>Reinvestment</th><th>FCFF</th><th>Present value</th></tr></thead><tbody>{scenario.evaluation.rows.map((row) => <tr key={row.year}>{[row.year, row.revenue, row.ebit, row.cash_tax, row.nopat, row.reinvestment, row.fcff, row.pv].map((v, i) => <td key={i}>{exact(v)}</td>)}</tr>)}</tbody></table></div><button className="text-button" onClick={() => inspect("Forecast and terminal", scenario.evaluation)}>Inspect terminal amounts and calculation evidence ↗</button></> : <p>N/A</p>}</details>
        <details className={styles.disclosure}><summary>Dated assumptions · model · policy</summary><p>Authored {payload.assumptions.authored_at} · {words(payload.assumptions.provenance)} · {payload.assumptions.retrospective ? "Retrospective" : "At valuation date"}</p><p>Model: {payload.model.revision} · Policy: {payload.policy.revision} · Effective: {payload.policy.effective_at}</p><dl>{Object.entries(assumption).map(([key, value]) => <div key={key}><dt>{words(key)}</dt><dd>{exact(value)}</dd></div>)}</dl><p>Forecast dates: {payload.assumptions.forecast_dates.join(" · ")}</p><button className="text-button" onClick={() => inspect("Assumptions and policy", payload.assumptions)}>Inspect full evidence ↗</button></details>
      </section> : null}
      {tab === "sensitivity" ? <section className={styles.panel} aria-label="Sensitivity"><div className={styles.sectionHeading}><h2>Sensitivity</h2>{grid ? <label>Grid<select aria-label="Grid" value={gridIndex} onChange={(event) => { setGridIndex(Number(event.target.value)); setCellIndex(0); }}>{payload.sensitivities.map((row, index) => <option key={row.name} value={index}>{row.name}</option>)}</select></label> : null}</div>{grid ? <>
        <p>{grid.output === "reverse_implied_parameter" ? "Conditional implied parameter · fraction" : `Conditional repricing · ${payload.currency} per share`} · Reference scenario: {grid.request.reference_scenario}</p>
        <div className={styles.tableWrap}><table><caption>{grid.name} · select an exact result to inspect</caption><thead><tr><th>{words(grid.request.x_parameter)}</th><th>{words(grid.request.y_parameter)}</th><th>Exact result · {words(grid.unit)}</th><th>State</th></tr></thead><tbody>{grid.cells.map((row, index) => <tr key={index}><td>{row.x}</td><td>{row.y}</td><td><button aria-pressed={cellIndex === index} onClick={() => setCellIndex(index)} className={styles.cell}>{exact(row.value)}</button></td><td>{row.solve ? states[row.solve.state] : row.value == null ? "Unavailable" : "Calculated"}</td></tr>)}</tbody></table></div>
        {cell ? <div className={styles.selectedCell} aria-live="polite"><h3>Selected sensitivity result</h3><p>{words(grid.request.x_parameter)}: {cell.x} · {words(grid.request.y_parameter)}: {cell.y}</p>{valueButton("Sensitivity result", cell.value, grid.unit === "fraction", { request: grid.request, cell })}<p>{cell.reasons.map(words).join(" · ")}</p><Terminal evaluation={cell.evaluation} />{cell.solve ? <SolverEvidence solve={cell.solve} /> : null}</div> : null}
        <div className={styles.tableWrap}><table><caption>Sensitivity effects · core-ranked within this grid</caption><thead><tr><th>Parameter</th><th>Elasticity</th><th>Rank</th><th>Reason</th></tr></thead><tbody>{grid.effects.map((effect) => <tr key={effect.parameter}><th>{words(effect.parameter)}</th><td><button className="text-button" onClick={() => inspect("Sensitivity effect", effect)}>{exact(effect.elasticity)}</button></td><td>{effect.rank ?? "N/A"}</td><td>{effect.reasons.map(words).join(" · ") || "Eligible"}</td></tr>)}</tbody></table></div>
      </> : <p>N/A</p>}</section> : null}
      <section className={styles.panel} aria-labelledby="bridge-title"><div className={styles.sectionHeading}><h2 id="bridge-title">Operating EV → common equity</h2><button className="text-button" onClick={() => inspect("EV to equity bridge", { bridge: payload.bridge, claims: payload.claims, shares: payload.shares })}>Inspect bridge evidence ↗</button></div><p>EV + cash + nonoperating assets − debt − leases − preferred − NCI − other claims</p><div className={styles.tableWrap}><table><caption>Economic claims · {payload.currency} · captured by {payload.bridge_captured_before}</caption><thead><tr><th>Component</th><th>Amount</th><th>State</th><th>As of</th></tr></thead><tbody>{payload.claims.map((claim) => <tr key={claim.kind}><th>{words(claim.kind)}</th><td>{valueButton(claim.kind, claim.amount, false, claim)}</td><td>{words(claim.state)}</td><td>{claim.as_of}</td></tr>)}</tbody></table></div><p>Bridge adjustment: {valueButton("Bridge adjustment", payload.bridge.adjustment, false, payload.bridge)} · Common shares: {valueButton("Common shares", payload.bridge.shares, false, payload.shares)}</p><p>{payload.bridge.eligible ? "Eligible bridge" : "Unavailable bridge"} {payload.bridge.reasons.map(words).join(" · ")}</p></section>
      <section className={styles.panel}><h2>Source measurement uncertainty</h2><dl>{payload.source_measurement_uncertainty.map(([name, value]) => <div key={name}><dt>{words(name)} · absolute source amount</dt><dd>{valueButton(name, value, false, payload.source_measurement_uncertainty)}</dd></div>)}</dl><p>Separate from the solver interval and the deterministic scenario span.</p><button className="text-button" onClick={() => inspect("Snapshot provenance", { reasons: payload.source_eligibility_reasons, selector: payload.source_selector })}>Inspect snapshot provenance ↗</button></section>
    </>}
    <footer className={styles.footer}><Link href="/development/company" prefetch={false}>Company fundamentals</Link><Link href="/help#valuation">Valuation guide</Link><span>Fictional S8a examples · no live inputs</span></footer>
  </main><EvidenceDrawer detail={detail} onClose={() => setDetail(undefined)} /></WorkbenchShell>;
}
