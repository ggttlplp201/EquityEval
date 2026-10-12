import "server-only";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { snapshotSha256 } from "./manifest";
import { safetySha256 } from "./safety-manifest";
import type { AnalysisReadinessSnapshot, SafetyReviewSnapshot } from "./types";

export async function loadAnalysisReadiness(): Promise<AnalysisReadinessSnapshot> {
  const bytes = await readFile(path.join(process.cwd(), "src/features/analysis-readiness/snapshot.json"));
  if (createHash("sha256").update(bytes).digest("hex") !== snapshotSha256) {
    throw new Error("Analysis-readiness snapshot verification failed");
  }
  return JSON.parse(bytes.toString("utf8")) as AnalysisReadinessSnapshot;
}

export async function loadSafetyReview(): Promise<SafetyReviewSnapshot> {
  const bytes = await readFile(path.join(process.cwd(), "src/features/analysis-readiness/safety.json"));
  if (createHash("sha256").update(bytes).digest("hex") !== safetySha256) {
    throw new Error("Safety-review snapshot verification failed");
  }
  return JSON.parse(bytes.toString("utf8")) as SafetyReviewSnapshot;
}
