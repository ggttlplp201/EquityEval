import type { Metadata } from "next";
import PipelineWorkspace from "@/features/pipeline/PipelineWorkspace";
import { loadNormalization } from "@/features/normalization/load";
import snapshot from "@/features/pipeline/snapshot";

export const metadata: Metadata = { title: "CRCL pipeline snapshot · EquityEval" };

export const dynamic = "force-dynamic";
export default async function PipelinePage() {
  const normalization = await loadNormalization();
  const data = { ...snapshot, stages: snapshot.stages.map((stage) => stage.id === "normalization" ? { ...stage, status: "verified" as const, statusLabel: "Published", summary: `${normalization.factCount} reviewed FY2025 facts` } : stage) };
  return <PipelineWorkspace data={data} normalization={{ batchId: normalization.batchId, factCount: normalization.factCount, publishedAt: normalization.publishedAt }} />;
}
