import type { FundamentalsPayload } from "@equity/schema/types/fundamentals";
export type SavedFundamentals = {
  example: string; years: 3 | 5 | 10; snapshot_id: string; input_snapshot_id: string;
  payload_hash: string; payload: FundamentalsPayload;
  chart_positions: Record<string, [string, string, string]>;
};
export type ExampleChoice = { id: string; label: string; basis: "annual" | "instant"; dates: string[] };
export type Bundle = { fictional: true; label: string; examples: ExampleChoice[]; snapshots: SavedFundamentals[] };
