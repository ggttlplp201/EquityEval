import type { Metadata } from "next";
import NormalizationWorkspace from "@/features/normalization/NormalizationWorkspace";
import { loadNormalization } from "@/features/normalization/load";

export const metadata: Metadata = { title: "CRCL normalized financials · EquityEval" };
export const dynamic = "force-dynamic";
export default async function NormalizationPage() {
  return <NormalizationWorkspace data={await loadNormalization()} />;
}
