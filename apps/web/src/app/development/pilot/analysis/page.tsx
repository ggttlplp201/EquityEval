import type { Metadata } from "next";
import AnalysisReadinessWorkspace from "@/features/analysis-readiness/AnalysisReadinessWorkspace";
import { loadAnalysisReadiness, loadSafetyReview, loadExhibitReview, loadCurrentReview, loadLeadershipReview, loadProspectusReview } from "@/features/analysis-readiness/load";

export const metadata: Metadata = { title: "CRCL analysis readiness · EquityEval" };
export const dynamic = "force-dynamic";

export default async function AnalysisReadinessPage() {
  const [data, safety, exhibits, current, leadership, prospectus] = await Promise.all([loadAnalysisReadiness(), loadSafetyReview(), loadExhibitReview(), loadCurrentReview(), loadLeadershipReview(), loadProspectusReview()]);
  return <AnalysisReadinessWorkspace data={data} safety={safety} exhibits={exhibits} current={current} leadership={leadership} prospectus={prospectus} />;
}
