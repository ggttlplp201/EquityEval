import type { Metadata } from "next";
import PipelineWorkspace from "@/features/pipeline/PipelineWorkspace";
import snapshot from "@/features/pipeline/snapshot";

export const metadata: Metadata = { title: "CRCL pipeline snapshot · EquityEval" };

export default function PipelinePage() {
  return <PipelineWorkspace data={snapshot} />;
}
