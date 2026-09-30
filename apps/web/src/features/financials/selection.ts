import type { Bundle, SavedFinancials } from "./types";

/** Choose one declared edition, never the first of ambiguous saved payloads. */
export function resolveSelection(bundle: Bundle, query: Record<string, string | string[] | undefined>): SavedFinancials | null {
  if (Object.keys(query).some((key) => !["basis", "edition"].includes(key)) || Object.values(query).some(Array.isArray)) return null;
  const basis = query.basis ?? "annual";
  if (basis !== "annual" && basis !== "quarter") return null;
  const edition = query.edition ?? (basis === "annual" ? "annual_original" : "quarter");
  const choices = bundle.choices.filter((choice) => choice.basis === basis && choice.edition === edition);
  if (choices.length !== 1) return null;
  const matches = bundle.snapshots.filter((saved) => saved.basis === basis && saved.edition === edition);
  return matches.length === 1 ? matches[0] : null;
}
