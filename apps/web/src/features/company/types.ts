/** Internal offline presentation contract, not the reviewed S6 API.
 * All financial values, labels, eligibility and plot coordinates come from Python.
 */
import type { Axis, CatalogEntry, EvidenceDetail } from "@/features/sectors/types";

export interface CompanyIdentity {
  id: string; ticker: string; name: string; sectorId: string; sectorLabel: string;
}
export interface CompanyMetric {
  id: string; label: string; unit: string; definition: string;
  value: string | null; valueLabel: string; status: string; statusLabel: string;
  reasons: string[]; reasonCodes: string[]; detailId: string;
}
export interface SourceAmount {
  label: string; value: string | null; valueLabel: string; basis: string;
  period: string; inputHash: string; flags: string; uncertainty: string; detailId: string;
}
export interface CompanyHistoryPoint {
  date: string; value: string | null; valueLabel: string; status: string;
  statusLabel: string; reasons: string[]; detailId: string; snapshotId: string;
  x: number; y: number | null;
}
export interface CompanyChart {
  points: CompanyHistoryPoint[]; paths: string[]; unavailableDates: string[];
  emptyReason: string | null; xAxis: Axis; yAxis: Axis;
}
export interface CompanyHistory {
  windowStart: string; windowEnd: string; coverageLabel: string;
  availableDates: string[]; missingDates: string[]; note: string;
  charts: Record<string, CompanyChart>;
}
export interface CompanyView {
  asOf: string; companyId: string; snapshotId: string; detailId: string; id: string;
  metrics: CompanyMetric[]; amounts: SourceAmount[]; history: Record<string, CompanyHistory>;
}
export interface CompanyBundle {
  fictional: true;
  context: {
    title: string; universe: string; taxonomy: string; membershipMode: string;
    period: string; currency: string; rulesVersion: string; policyVersion: string;
    asOfDates: string[]; defaultAsOf: string; defaultSectorId: string; defaultCompanyId: string;
    sourceSnapshotId: string; prerequisites: string[]; historyNote: string;
  };
  companies: CompanyIdentity[]; metrics: CatalogEntry[];
  views: Record<string, CompanyView>; details: Record<string, EvidenceDetail>;
}
export interface CompanyPageData extends Omit<CompanyBundle, "views"> {
  company: CompanyIdentity; selectedAsOf: string; views: CompanyView[];
}
