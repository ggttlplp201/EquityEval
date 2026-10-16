import type { RealSnapshotResponse } from "@equity/schema/types/real-fundamentals";
import type { EvidenceDetail } from "@/features/sectors/types";

export interface BroaderFundamentalsView {
  kind: "published-real-crcl-broader";
  sourceObservation: string;
  bodyCount: number;
  comparisonCount: number;
  findings: Record<string, string>;
  missingHistory: { resourceKey: string; form: string; filedDate: string; reason: string; acquisitionContract: string }[];
  comparativeRows: { id: string; label: string; period: string; display: string }[];
  results: {
    basis: "annual" | "instant";
    snapshot: RealSnapshotResponse;
    metrics: { id: string; metricId: string; label: string; display: string; scope: string }[];
    gaps: { id: string; label: string; requirement: string; reasons: string[] }[];
    operands: { id: string; label: string; display: string }[];
    accountingDetail: string;
  }[];
  details: Record<string, EvidenceDetail>;
}
