/** Internal, generated demonstration view model. This is not the S6 API contract.
 * Financial arithmetic and eligibility are computed by equity_core in Python.
 * Coordinates and labels are supplied by the offline presentation exporter.
 */
export interface EvidenceDetail {
  title: string;
  subtitle: string;
  sections: { heading: string; rows: { label: string; value: string }[] }[];
  sources: { label: string; url?: string; accession?: string; capturedAt: string; transform: string; licence: string }[];
}
export interface CatalogEntry { id: string; label: string; definition: string; unit?: string }
export interface Sector { id: string; label: string; color: string; parentId?: string }
export interface Axis { ticks: { position: number; label: string }[]; zero: number }
export interface Company {
  id: string; ticker: string; name: string; valueLabel: string; status: string;
  reasons: string[]; detailId: string; position: number | null; snapshotId?: string;
}
export interface SectorRow {
  sectorId: string; valueLabel: string; value: string | null; status: string;
  statusLabel: string; reasons: string[]; coverageLabel: string; capCoverageLabel: string;
  countsLabel: string; eligibilityLabel: string; detailId: string; observations: string[];
  concentration: { currentShareLabel: string; currentDate: string; growthLabel: string; priorDate: string | null; excludedIds: string[]; reasons: string[] } | null;
  bar: { left: number; width: number; endpoint: number } | null;
}
export interface Distribution {
  detailId: string;
  bins: { id: string; label: string; countLabel: string; companyIds: string[]; x: number; y: number; width: number; height: number }[];
  markers: { label: string; x: number; valueLabel: string }[];
  xAxis: Axis; yAxis: Axis; companies: Company[];
  excluded: { label: string; count: number }[]; emptyReason: string | null;
}
export interface HistoryPoint { asOf: string; x: number; y: number | null; valueLabel: string; status: string; detailId: string }
export interface HistoryPlot {
  xAxis: Axis; yAxis: Axis;
  series: { sectorId: string; paths: string[]; points: HistoryPoint[] }[];
  note: string;
}
export interface ScatterPlot {
  xAxis: Axis; yAxis: Axis; xLabel: string; yLabel: string;
  points: { sectorId: string; x: number; y: number; radius: number; xLabel: string; yLabel: string; detailId: string; growthDetailId: string }[];
  unavailable: { sectorId: string; reason: string }[];
}
export interface SectorView {
  id: string; asOf: string; metricId: string; method: string; definition: string;
  rows: SectorRow[]; orders: { alphabetical: string[]; numeric: string[] };
  axis: Axis; market: SectorRow | null;
  history: Record<string, HistoryPlot>;
  distributions: Record<string, Distribution>;
  scatter: ScatterPlot;
}
export interface SectorBundle {
  fictional: true;
  context: {
    title: string; universe: string; taxonomy: string; membershipMode: string;
    period: string; currency: string; rulesVersion: string; policyVersion: string;
    asOfDates: string[]; defaultAsOf: string; defaultSectorId: string;
    sourceSnapshotId: string; prerequisites: string[];
  };
  sectors: Sector[]; metrics: CatalogEntry[]; methods: CatalogEntry[];
  views: Record<string, SectorView>; details: Record<string, EvidenceDetail>;
}
