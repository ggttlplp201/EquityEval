import type { EvidenceDetail } from "@/features/sectors/types";

/** Checked local presentation of real S3 rows; not a financial-analysis API. */
export interface NormalizationSnapshot {
  kind: "real-crcl-normalization";
  batchId: string; publishedAt: string; periodLabel: string; retrievalCutoff: string;
  factCount: number; captureCount: number; flagCount: number;
  views: Record<string, { label: string; facts: { id: string; label: string; value: string | null; detailId: string }[] }>;
  details: Record<string, EvidenceDetail>;
}
