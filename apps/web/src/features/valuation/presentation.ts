import type { Interval, ScenarioResult, SolveResult, ValuationPayload } from "@equity/schema/types/valuation";

export const states: Record<SolveResult["state"], string> = {
  converged: "Unique solution",
  no_solution_in_domain: "No solution in domain",
  non_unique: "Multiple solutions",
  inconclusive: "Inconclusive",
  unavailable: "Unavailable",
};
export function words(value: string): string { return value.replaceAll("_", " "); }
// Presentation only: round saved decimal digits, never convert them through a float.
// Halfway values round away from zero; percent shifts the decimal point first.
function decimal(value: string, percent = false): string {
  const match = /^([+-]?)(?:(0|[1-9]\d*)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?$/.exec(value);
  if (!match) return value;
  const fraction = match[3] ?? match[4] ?? "";
  const exponent = Number(match[5] ?? 0);
  // Public Decimal inputs are bounded; do not expand arbitrary metadata-sized exponents.
  if (!Number.isSafeInteger(exponent) || Math.abs(exponent) > 1000) return value;
  const coefficient = BigInt((match[2] ?? "0") + fraction);
  const shift = exponent - fraction.length + (percent ? 2 : 0) + 4;
  let units: bigint;
  if (shift >= 0) units = coefficient * 10n ** BigInt(shift);
  else {
    const divisor = 10n ** BigInt(-shift);
    units = coefficient / divisor + (coefficient % divisor * 2n >= divisor ? 1n : 0n);
  }
  const digits = units.toString().padStart(5, "0");
  const tail = digits.slice(-4).replace(/0+$/, "");
  const sign = units === 0n ? "" : match[1];
  return `${sign}${digits.slice(0, -4)}${tail ? `.${tail}` : ""}`;
}

// Only traverse known numeric/interval fields in solver and assumption displays.
// Unrecognized subtrees (including IDs, dates, hashes, names and reasons) stay exact.
const numericFields = new Set([
  "lower", "upper", "absolute_tolerance", "relative_tolerance", "width_tolerance",
  "anchor_margin", "margin_weights", "max_evaluations", "max_iterations", "max_subdivisions",
  "evaluations", "iterations", "subdivisions", "representative",
  "growth", "margins", "reinvestment", "revenue_anchor", "risk_free", "taxes",
  "terminal_growth", "terminal_margin", "terminal_roic", "terminal_tax", "wacc",
]);
const intervalFields = new Set([
  "solve", "proof", "interval", "root_intervals", "unresolved_domains", "domain",
  "derivative", "residual", "left_residual", "right_residual", "root",
]);
function displayProjection(value: unknown): unknown {
  if (typeof value === "string" || typeof value === "number") return decimal(String(value));
  if (Array.isArray(value)) return value.map(displayProjection);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, item]) => [
    key, numericFields.has(key) || intervalFields.has(key) ? displayProjection(item) : item,
  ]));
  return value;
}
/** Root scalars are numeric controls; structured values use known numeric fields only. */
export function rounded(value: unknown): string { return exact(displayProjection(value)); }
export function number(value: string | null | undefined, percent = false): string {
  if (value == null) return "N/A";
  const display = decimal(value, percent);
  const [whole, fraction] = display.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${grouped}${fraction ? `.${fraction}` : ""}${percent ? "%" : ""}`;
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
