import type { Metadata } from "next";
import AnalysisReadinessWorkspace from "@/features/analysis-readiness/AnalysisReadinessWorkspace";
import { loadRealFundamentals, loadAnalysisReadiness, loadSafetyReview, loadExhibitReview, loadCurrentReview, loadLeadershipReview, loadProspectusReview, loadRegistrationReview, loadObservationReview } from "@/features/analysis-readiness/load";

export const metadata: Metadata = { title: "CRCL analysis readiness · EquityEval" };
export const dynamic = "force-dynamic";

export default async function AnalysisReadinessPage() {
  const [real, data, safety, exhibits, current, leadership, prospectus, registration, observation] = await Promise.all([loadRealFundamentals(), loadAnalysisReadiness(), loadSafetyReview(), loadExhibitReview(), loadCurrentReview(), loadLeadershipReview(), loadProspectusReview(), loadRegistrationReview(), loadObservationReview()]);
  return <AnalysisReadinessWorkspace real={real} data={data} safety={safety} exhibits={exhibits} current={current} leadership={leadership} prospectus={prospectus} registration={registration} observation={observation} />;
}
