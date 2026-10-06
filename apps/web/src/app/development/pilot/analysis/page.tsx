import type { Metadata } from "next";
import AnalysisReadinessWorkspace from "@/features/analysis-readiness/AnalysisReadinessWorkspace";
import { loadAnalysisReadiness } from "@/features/analysis-readiness/load";

export const metadata: Metadata = { title: "CRCL analysis readiness · EquityEval" };
export const dynamic = "force-dynamic";

export default async function AnalysisReadinessPage() {
  return <AnalysisReadinessWorkspace data={await loadAnalysisReadiness()} />;
}
