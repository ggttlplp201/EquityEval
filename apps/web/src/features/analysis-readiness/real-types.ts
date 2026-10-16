import type { RealSnapshotResponse } from "@equity/schema/types/real-fundamentals";
import type { EvidenceDetail } from "@/features/sectors/types";

export interface RealFundamentalsView {
  kind: "published-real-crcl-fundamentals";
  snapshot: RealSnapshotResponse;
  marginDisplay: string;
  sourceObservation: string;
  evaluatedAt: string;
  operands: { id: string; label: string; display: string }[];
  unresolved: { id: string; label: string; requirement: string }[];
  details: Record<string, EvidenceDetail>;
}
