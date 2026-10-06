import type { Metadata } from "next";
import PipelineWorkspace from "@/features/pipeline/PipelineWorkspace";
import { loadAnalysisReadiness } from "@/features/analysis-readiness/load";
import { loadNormalization } from "@/features/normalization/load";
import snapshot from "@/features/pipeline/snapshot";

export const metadata: Metadata = { title: "CRCL pipeline snapshot · EquityEval" };

export const dynamic = "force-dynamic";
export default async function PipelinePage() {
  const [normalization, readiness] = await Promise.all([loadNormalization(), loadAnalysisReadiness()]);
  const data = { ...snapshot, stages: snapshot.stages.map((stage) => {
    if (stage.id === "normalization") return { ...stage, status: "verified" as const, statusLabel: "Published", summary: `${normalization.factCount} reviewed FY2025 facts` };
    if (stage.id === "analysis") return { ...stage, status: "blocked" as const, statusLabel: "Blocked", summary: `${readiness.sourceInputCount} normalized inputs; ${readiness.publishedMetricCount} published metrics` };
    return stage;
  }) };
  return <PipelineWorkspace data={data} normalization={{ batchId: normalization.batchId, factCount: normalization.factCount, publishedAt: normalization.publishedAt }} readiness={{ sourceInputCount: readiness.sourceInputCount, publishedMetricCount: readiness.publishedMetricCount }} />;
}
