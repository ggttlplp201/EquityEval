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

export interface SafetyReviewSnapshot {
  kind: "real-crcl-safety-review";
  reviewedOn: string;
  period: string;
  inventoryWindow: string;
  historicalRetrievalCutoff: string;
  historicalDecision: { status: "blocked"; explanation: string; reasonCodes: string[] };
  retrospectiveDecision: { status: "incomplete"; explanation: string; reasonCodes: string[] };
  operatingMargin: null;
  publishedMetricCount: 0;
  filings: {
    accession: string; form: string; filedDate: string; acceptedAt: string;
    reportPeriodEnd: string | null; items: string; url: string;
    bodyStatus: "retained_at_cutoff" | "retrospective_only" | "missing";
    availableAtHistoricalCutoff: boolean; captureId: string | null;
    completedAt: string | null; bodySha256: string | null;
    metadataCaptureId: string; metadataLocator: string;
    eventReview: string; reviewSummary: string;
  }[];
  checks: { id: string; label: string; status: string; explanation: string; detailId: string }[];
  details: Record<string, EvidenceDetail>;
  profile: { business_model: string; revision: string; known_on: string; effective_on: string };
  profileNotes: string[];
  inventorySource: { url: string; capturedAt: string };
  missingExhibits: { accession: string; label: string; url: string; status: string }[];
  freshInventory: {
    source: { url: string; capturedAt: string };
    outsidePinnedWindow: { accession: string; form: string; filedDate: string; url: string }[];
  };
  acquisition: { status: string; note: string };
  nextStep: string;
}

export interface ExhibitReviewSnapshot {
  kind: "real-crcl-exhibit-review";
  reviewedOn: string;
  historicalRetrievalCutoff: string;
  reviewedCount: number;
  conclusion: string;
  blockers: string[];
  nextStep: string;
  operatingMargin: null;
  publishedMetricCount: 0;
  exhibits: {
    id: string; accession: string; form: string; filedDate: string; items: string;
    exhibit: string; label: string; url: string; status: string;
    scope: string; relevance: string; finding: string; limit: string;
    captureId: string | null; capturedAt: string | null; sha256: string | null;
  }[];
  details: Record<string, EvidenceDetail>;
  freshInventory: null | {
    source: { url: string; capturedAt: string };
    outsidePinnedWindow: { accession: string; form: string; filedDate: string; url: string }[];
  };
}

export interface CurrentReviewSnapshot {
  kind: "real-crcl-current-review";
  reviewedOn: string;
  inventoryObservedAt: string | null;
  retrievalCutoff: string | null;
  historicalRetrievalCutoff: string;
  conclusion: string;
  cutoffNote: string;
  nextStep: string;
  candidateBatch: { status: string; batchId: null; reasonCodes: string[]; explanation: string };
  events: { id: string; accession: string; title: string; filedDate: string; form: string;
    items?: string; status: string; finding: string; limit: string; capturedAt: string | null }[];
  missingBodies: { resourceKey: string; accession: string; exhibit: string; url: string; reason: string }[];
  reconciliation: { id: string; label: string; status: string; finding: string; detailId: string }[];
  annualEditionChecks: { concept: string; status: string; reason: string }[];
  details: Record<string, EvidenceDetail>;
  currentInventory: null | { status: string; count: number; forms: string[]; boundaryStart: string;
    boundaryEnd: string; note: string; source: { url: string; capturedAt: string } };
}
