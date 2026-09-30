import type { ValuationPayload } from "@equity/schema/types/valuation";
export type Example = { id: string; label: string; payload: ValuationPayload | null };
export type Bundle = { fictional: true; examples: Example[] };
