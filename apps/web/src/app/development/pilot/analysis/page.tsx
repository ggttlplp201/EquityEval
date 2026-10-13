import type { Metadata } from "next";
import AnalysisReadinessWorkspace from "@/features/analysis-readiness/AnalysisReadinessWorkspace";
import { loadAnalysisReadiness, loadSafetyReview, loadExhibitReview, loadCurrentReview, loadLeadershipReview } from "@/features/analysis-readiness/load";

export const metadata: Metadata = { title: "CRCL analysis readiness · EquityEval" };
export const dynamic = "force-dynamic";

export default async function AnalysisReadinessPage() {
  const [data, safety, exhibits, current, leadership] = await Promise.all([loadAnalysisReadiness(), loadSafetyReview(), loadExhibitReview(), loadCurrentReview(), loadLeadershipReview()]);
  return <AnalysisReadinessWorkspace data={data} safety={safety} exhibits={exhibits} current={current} leadership={leadership} />;
}
