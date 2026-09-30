import type { Interval, SolveResult } from "@equity/schema/types/valuation";

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
