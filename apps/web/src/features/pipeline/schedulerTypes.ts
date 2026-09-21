export interface SchedulerSnapshot {
  kind: "real-filing-scheduler-snapshot";
  asOf: string; auditSha256: string; scheduleId: string; revisionId: string;
  epoch: number; configSha256: string; active: boolean; health: string;
  service: "not_configured"; healthMeaning: string; reasons: string[];
  filedStart: string; filedEnd: string; cadenceSeconds: number; jitterSeconds: number;
  budgetUnits: number; reservedUnits: number; actualAttempts: number;
  lastTickAt: string | null; lastHttpCompletedAt: string | null;
  lastSuccessAt: string | null; lastSuccessCutoff: string | null;
  nextDueAt: string; nextDueActionable: boolean; lagSeconds: number;
  retryAt: string | null; failures: number;
  missedIntervals: { first: number; last: number; count: number; reason: string }[];
  slots: {
    index: number; requestId: string; executionId: string; nominalAt: string; dueAt: string;
    state: string; availableAt: string; attemptNumber: number; outcome: string | null; outcomeLabel: string; checkedAt: string | null;
    eligible: boolean; manifestSha256: string | null; planSha256: string;
    baselineRequestId: string; baselineManifestSha256: string;
    filings: number | null; newFilings: number | null; amendments: number | null;
    coverage: { baseline: string; current: string } | null;
  }[];
  attempts: {
    id: string; state: string; status: number | null; requestedAt: string | null;
    finishedAt: string | null; payloadSha256: string | null; payloadBytes: number | null;
    reusedCaptureId: string | null;
  }[];
  revisions: { epoch: number; at: string; active: boolean; reason: string; configSha256: string }[];
  events: { kind: string; at: string; key: string }[];
  counts: { id: string; value: number }[];
}
