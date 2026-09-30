import "server-only";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { snapshotSha256 } from "./manifest";
import type { NormalizationSnapshot } from "./types";

export async function loadNormalization(): Promise<NormalizationSnapshot> {
  const bytes = await readFile(path.join(process.cwd(), "src/features/normalization/snapshot.json"));
  if (createHash("sha256").update(bytes).digest("hex") !== snapshotSha256) throw new Error("Normalization snapshot verification failed");
  return JSON.parse(bytes.toString("utf8")) as NormalizationSnapshot;
}
