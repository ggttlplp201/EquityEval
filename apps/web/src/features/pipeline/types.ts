/** Internal presentation only. No live database connection or S6 public API. */
export type PipelineStageId = "plan" | "captures" | "identity" | "registration" | "normalization" | "analysis";
export interface PipelineEvidence { captureId: string; locator: string; excerpt: string }
export interface PipelineCapture {
  id: string; label: string; url: string; sha256: string; bytes: number;
  httpStatus: number; requestedAt: string; capturedAt: string;
}
export interface PipelineField {
  id: string; label: string; value: string | null;
  status: "supported" | "unsubstantiated"; evidence: PipelineEvidence[];
}
export interface PipelineStage {
  id: PipelineStageId; number: string; label: string;
  status: "verified" | "gap" | "blocked" | "not-started";
  statusLabel: string; summary: string;
}
export interface CurrencySearch {
  reviewedOn: string; sha256: string; basis: string; summary: string;
  effectiveDateRule: string; nextAction: string;
  sources: { id: string; label: string; url: string; statusLabel: string;
    method: string; finding: string; dateContext: string; policy: string;
    links: { label: string; url: string }[] }[];
}
export interface PipelineSnapshot {
  kind: "real-application-pipeline-snapshot"; ticker: "CRCL"; reviewedOn: string;
  acquisitionVerifiedAt: string; reviewCheckpoint: string; requestId: string; executionId: string;
  acquisitionAuditSha256: string; identityAuditSha256: string;
  counts: { id: string; label: string; value: number }[];
  captures: PipelineCapture[]; identityFields: PipelineField[];
  reportingCurrencyEvidence: PipelineEvidence[];
  plan: { inventoryStart: string; inventoryEnd: string; resources: string[]; hash: string; policy: string };
  blocker: { code: "quote_currency_unsubstantiated"; title: string; explanation: string; nextAction: string };
  currencySearch: CurrencySearch;
  stages: PipelineStage[];
}
