import "server-only";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { snapshotSha256 } from "./manifest";
import type { AnalysisReadinessSnapshot } from "./types";

export async function loadAnalysisReadiness(): Promise<AnalysisReadinessSnapshot> {
  const bytes = await readFile(path.join(process.cwd(), "src/features/analysis-readiness/snapshot.json"));
  if (createHash("sha256").update(bytes).digest("hex") !== snapshotSha256) {
    throw new Error("Analysis-readiness snapshot verification failed");
  }
  return JSON.parse(bytes.toString("utf8")) as AnalysisReadinessSnapshot;
}
