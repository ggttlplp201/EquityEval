/** Internal archived-evidence presentation only; not the reviewed S6 public API.
 * Source values and labels are supplied by the Python export. This slice has no
 * derived metrics, price feed, valuation output or eligible history series.
 */
import type { EvidenceDetail } from "@/features/sectors/types";

export const PILOT_TICKERS = ["CRCL", "MSTR", "COIN", "HOOD", "USAR", "MP", "GOOGL"] as const;
export type PilotTicker = typeof PILOT_TICKERS[number];
export type PilotHistoryWindow = "3" | "5" | "10";

export interface PilotFiling {
  accession: string; form: string; periodEnd: string; filed: string; url: string;
}
export interface PilotObservedFiling extends PilotFiling {
  periodStart: string; capturedAt: string; companyfactsCapturedAt: string;
}
export interface PilotAmount {
  id: string; label: string; value: string | null; valueLabel: string;
  period: string; detailId: string; statusLabel: string;
}
export interface PilotMetric {
  id: string; label: string; value: null; valueLabel: string;
  statusLabel: string; reasons: string[]; detailId: string | null;
}
export interface PilotGap { area: string; reason: string }
export interface PilotHistory {
  windowStart: string; windowEnd: string; coverageLabel: string; note: string;
}
export interface PilotCompany {
  ticker: PilotTicker; cik: string; name: string; security: string; exchange: string;
  identityDate: string; identityUrl: string; businessSummary: string;
  businessEvidenceDate: string; businessEvidenceUrl: string; filing: PilotFiling;
  observedFiling?: PilotObservedFiling; amounts: PilotAmount[]; metrics: PilotMetric[];
  gaps: PilotGap[]; history: Record<PilotHistoryWindow, PilotHistory>;
}
export interface PilotBundle {
  kind: "real-source-pilot"; reviewedAt: string; snapshotId: string;
  companies: PilotCompany[]; details: Record<string, EvidenceDetail>;
}
export interface PilotRosterEntry {
  ticker: PilotTicker; name: string; hasObservedAmounts: boolean; gaps: PilotGap[];
}
export interface PilotPageData extends Omit<PilotBundle, "companies"> {
  company: PilotCompany; roster: PilotRosterEntry[];
}
