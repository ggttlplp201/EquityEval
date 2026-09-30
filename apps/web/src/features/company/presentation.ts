import { number } from "@/features/valuation/presentation";

/** Display-only rounding of saved decimals, preserving their supplied unit. */
export function valueLabel(value: string | null, unit?: string): string {
  if (value === null) return "N/A";
  const display = number(value, unit === "fraction");
  return unit === "USD" ? `$${display}` : unit === "multiple" ? `${display}×` : display;
}
