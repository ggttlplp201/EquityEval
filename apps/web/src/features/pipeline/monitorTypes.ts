/** Internal saved D4a presentation, not a live service or S6 API. */
export interface MonitoredFiling {
  accession: string; form: string; filedDate: string; reportDate: string | null;
  acceptanceAt: string; sourceLocator: string; captureId: string;
  capturedAt: string; url: string; sha256: string;
}
export interface MonitorSnapshot {
  kind: "real-filing-monitor-snapshot";
  outcome: "no_change" | "new_filing" | "amendment" | "mixed_changes" | "incomplete" | "error";
  outcomeLabel: string; baselineEligible: boolean; checkedAt: string | null;
  requestId: string; executionId: string; requestSha256: string; auditSha256: string; manifestSha256: string;
  baseline: { kind: string; requestId: string; executionId: string; cutoff: string; manifestSha256: string; captureIds: string[] };
  cutoff: string; filedStart: string; filedEnd: string; forms: string[];
  coverage: { baseline: string; current: string }; flags: string[];
  newFilings: MonitoredFiling[]; amendments: MonitoredFiling[]; filings: MonitoredFiling[];
  filingCount: number; newCount: number; amendmentCount: number;
  blockers: string[]; knownLimits: string; amendmentMeaning: string;
  history: { baseline: { required: string[]; excluded_nonoverlap: string[] } | null;
    current: { required: string[]; excluded_nonoverlap: string[] } | null };
  attempts: { id: string; status: number | null; state: string; requestedAt: string | null;
    finishedAt: string | null; reusedCaptureId: string | null; payloadSha256: string | null; payloadBytes: number | null }[];
  counts: { id: string; label: string; value: number }[];
}
