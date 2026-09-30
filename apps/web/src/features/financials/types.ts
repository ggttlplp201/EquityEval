import type { Concept } from "@equity/schema/types/concepts";

export type Basis = "annual" | "quarter";
export type Family = "income" | "balance_sheet" | "cash_flow";
export type Choice = { edition: string; label: string; basis: Basis };
export type Period = { id: string; period_kind: "duration" | "instant"; start_date: string | null; end_date: string };
export type SourceEvidence = {
  evidence_id: string; source_id: string; source_hash: string; fixture_source: string;
  source_locator: string; source_tag: string; accession: null; original_numeric_text: string | null;
  filed_on: string; known_on: string; retrieved_at: string; period: Period;
  unit: { id: string; unit_key: "USD"; numerator_measures: string[]; denominator_measures: string[] };
  currency: "USD"; scale: "1"; scope: "consolidated"; statement: Family; reporting_basis: "us_gaap";
  restatement_status: "original" | "repeated" | "restated" | "unavailable";
  prior_evidence_id: string | null; prior_value: string | null;
  transform: { operation: "identity_decimal"; revision: string };
};
export type StatementRow = { concept: Concept; label: string; value: string | null; status: "reported" | "missing"; quality_flags: string[]; evidence: SourceEvidence };
export type SavedFinancials = Choice & {
  company: string; issuer_id: string; source_id: string; input_hash: string;
  currency: "USD"; scale: "1"; scope: "consolidated"; filed_on: string; known_on: string; retrieved_at: string;
  history_mode: "original_as_filed" | "latest_reported"; supersedes: string | null;
  revision: string; payload_hash: string; snapshot_id: string;
  statements: { family: Family; period: Period; rows: StatementRow[]; coverage: { available: number; requested: number; scope: "selected_lines" } }[];
};
export type Bundle = { fictional: true; label: string; choices: Choice[]; snapshots: SavedFinancials[] };
