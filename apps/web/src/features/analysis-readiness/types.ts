import type { EvidenceDetail } from "@/features/sectors/types";

export type ReadinessStatus = "blocked" | "not_reviewed" | "not_implemented";

export interface AnalysisReadinessSnapshot {
  kind: "real-crcl-analysis-readiness";
  company: { ticker: "CRCL"; name: string };
  batchId: string;
  periodLabel: string;
  sourceInputCount: number;
  publishedMetricCount: 0;
  status: "blocked";
  inputs: {
    id: "revenue" | "operating_income";
    label: string;
    exactValue: string;
    displayValue: string;
    unit: "USD";
    status: "normalized_unusable";
    analysisValue: null;
    detailId: string;
    reasonCodes: string[];
    sourceChainCaptureIds: string[];
  }[];
  details: Record<string, EvidenceDetail>;
  candidateMetric: {
    id: "operating_margin";
    label: string;
    formula: string;
    value: null;
    displayValue: "N/A";
    unit: "percent";
    status: "blocked";
    reasonCodes: string[];
    requiredInputIds: string[];
  };
  gates: { id: string; label: string; status: ReadinessStatus; reason: string }[];
  source: {
    normalizationHref: string;
    publishedAt: string;
    retrievalCutoff: string;
    snapshotSha256: string;
  };
}
