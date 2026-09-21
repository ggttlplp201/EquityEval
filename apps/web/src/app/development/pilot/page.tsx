import { readFile } from "node:fs/promises";
import path from "node:path";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import PilotWorkspace from "@/features/pilot/PilotWorkspace";
import { PILOT_TICKERS, type PilotBundle } from "@/features/pilot/types";

export const metadata: Metadata = { title: "Real-data pilot · EquityEval" };

export default async function PilotPage({ searchParams }: {
  searchParams: Promise<{ company?: string | string[] }>;
}) {
  const query = await searchParams;
  if (Array.isArray(query.company)) notFound();
  const ticker = query.company ?? "CRCL";
  if (!PILOT_TICKERS.some((item) => item === ticker)) notFound();

  const file = path.join(process.cwd(), "src/features/pilot/evidence.json");
  const bundle = JSON.parse(await readFile(file, "utf8")) as PilotBundle;
  if (bundle.kind !== "real-source-pilot"
    || bundle.companies.length !== PILOT_TICKERS.length
    || bundle.companies.some((company, index) => company.ticker !== PILOT_TICKERS[index])) {
    throw new Error("The archived pilot requires its exact reviewed seven-company roster.");
  }
  const company = bundle.companies.find((item) => item.ticker === ticker);
  if (!company) notFound();
  if (company.metrics.some((metric) => metric.value !== null)) {
    throw new Error("The archived source pilot does not support derived metric values.");
  }
  const detailIds = new Set([
    ...company.amounts.map((amount) => amount.detailId),
    ...company.metrics.flatMap((metric) => metric.detailId ? [metric.detailId] : []),
  ]);
  if ([...detailIds].some((id) => !bundle.details[id])) {
    throw new Error("An archived source amount is missing its exact evidence detail.");
  }
  // Financial amounts and source details are sent for this selection only.
  // The roster contains navigation and gap descriptions, not other issuers' facts.
  const details = Object.fromEntries(Object.entries(bundle.details).filter(([id]) => detailIds.has(id)));
  const roster = bundle.companies.map((item) => ({
    ticker: item.ticker, name: item.name, hasObservedAmounts: item.amounts.length > 0, gaps: item.gaps,
  }));
  return <PilotWorkspace key={ticker} data={{
    kind: bundle.kind, reviewedAt: bundle.reviewedAt, snapshotId: bundle.snapshotId,
    company, roster, details,
  }} />;
}
