import type { Bundle, SavedFundamentals } from "./types";

/** Exact, fail-closed lookup: never choose the first of ambiguous saved candidates. */
export function resolveSelection(bundle: Bundle, query: Record<string, string | string[] | undefined>): SavedFundamentals | null {
  if (Object.keys(query).some((key) => !["example", "date", "years"].includes(key)) || Object.values(query).some(Array.isArray)) return null;
  if (query.years !== undefined && !["3", "5", "10"].includes(String(query.years))) return null;
  const choices = bundle.examples.filter((row) => row.id === (query.example ?? "reference"));
  if (choices.length !== 1) return null;
  const choice = choices[0];
  if (new Set(choice.dates).size !== choice.dates.length) return null;
  const date = query.date ?? choice.dates.at(-1);
  if (typeof date !== "string" || !choice.dates.includes(date)) return null;
  const snapshots = bundle.snapshots.filter((row) => row.example === choice.id && row.payload.selector.as_of === date && String(row.years) === (query.years ?? "3"));
  return snapshots.length === 1 ? snapshots[0] : null;
}
