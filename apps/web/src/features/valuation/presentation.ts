import type { Interval, ScenarioResult, SolveResult, ValuationPayload } from "@equity/schema/types/valuation";

export const states: Record<SolveResult["state"], string> = {
  converged: "Unique solution",
  no_solution_in_domain: "No solution in domain",
  non_unique: "Multiple solutions",
  inconclusive: "Inconclusive",
  unavailable: "Unavailable",
};
export function words(value: string): string { return value.replaceAll("_", " "); }
// Display formatting only. Exact decimal strings are retained in the evidence tables.
export function number(value: string | null | undefined, percent = false): string {
  if (value == null) return "N/A";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 4, style: percent ? "percent" : "decimal" }).format(Number(value));
}
export function interval(value: Interval | null | undefined, percent = false): string {
  return value ? `${number(value.lower, percent)} – ${number(value.upper, percent)}` : "N/A";
}
export function exact(value: unknown): string {
  return value == null ? "N/A" : typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

// Eligibility labels only: the saved core span is never computed in the browser.
export function spanStatus(payload: ValuationPayload | null): { eligible: boolean; label: string } {
  if (!payload) return { eligible: false, label: "Missing saved result" };
  const reasons = payload.scenarios.flatMap((scenario) => {
    if (!scenario.name.trim()) return ["Unnamed scenario"];
    if (scenario.solve.state !== "converged") return [`${scenario.name}: ${states[scenario.solve.state]}`];
    return scenario.solve.representative === null ? [`${scenario.name}: saved representative unavailable`] : [];
  });
  const declared = new Set(payload.assumptions.scenarios.map((scenario) => scenario.name));
  const returned = new Set(payload.scenarios.map((scenario) => scenario.name));
  if (declared.size !== payload.assumptions.scenarios.length || returned.size !== payload.scenarios.length || declared.size !== returned.size || [...declared].some((name) => !returned.has(name))) {
    reasons.push("Declared scenario roster is incomplete or duplicated");
  }
  if (payload.scenarios.length < 2) reasons.push("at least two named scenarios required");
  if (!reasons.length && payload.scenario_dispersion === null) reasons.push("Saved scenario span unavailable");
  return { eligible: reasons.length === 0, label: reasons.length ? reasons.join("; ") : "Complete eligible named roster" };
}

// Pass through exact strings; never reconstruct the equity bridge or per-share result.
export function bridgeEndpoints(payload: ValuationPayload, scenario: ScenarioResult | undefined) {
  const converged = scenario?.solve.state === "converged";
  return [
    { id: "operating_ev", label: "Selected operating EV", value: converged ? scenario.evaluation?.operating_ev ?? null : null },
    { id: "adjustment", label: "Bridge adjustment", value: payload.bridge.adjustment },
    { id: "common_equity", label: "Selected common equity", value: converged ? scenario.common_equity : null },
    { id: "shares", label: "Common shares", value: payload.bridge.shares },
    { id: "conditional_per_share", label: "Conditional value per share", value: converged ? scenario.conditional_per_share : null },
  ];
}
