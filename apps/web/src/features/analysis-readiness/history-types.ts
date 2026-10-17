import type { EvidenceDetail } from "@/features/sectors/types";

export interface HistoryReviewView {
  kind: "d5l-blocked-history-review";
  status: "blocked";
  retainedBodyCount: number;
  acquisitionCompletedAt: string;
  filingDateScopeEnd: string;
  postBodyObservation: null;
  cutoffNote: string;
  reviewLimit: string;
  nextStep: string;
  blockers: string[];
  metrics: { id: string; value: null; status: string; reason: string }[];
  bodies: { accession: string; form: string; filedDate: string; resourceKey: string; retained: boolean; status: string; finding: string; actualContentType: string | null }[];
  details: Record<string, EvidenceDetail>;
}
