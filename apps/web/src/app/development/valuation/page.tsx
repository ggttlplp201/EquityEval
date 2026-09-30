import { readFile } from "node:fs/promises";
import path from "node:path";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import ValuationWorkspace from "@/features/valuation/ValuationWorkspace";
import type { Bundle } from "@/features/valuation/types";

export const metadata: Metadata = { title: "Reverse DCF · EquityEval" };
export default async function ValuationPage({ searchParams }: {
  searchParams: Promise<{ example?: string | string[] }>;
}) {
  const query = await searchParams;
  if (Array.isArray(query.example)) notFound();
  const bundle = JSON.parse(await readFile(path.join(process.cwd(), "src/features/valuation/fixture.json"), "utf8")) as Bundle;
  if (bundle.fictional !== true) throw new Error("Fictional valuation fixture required");
  const selected = bundle.examples.find((row) => row.id === (query.example ?? "reference"));
  if (!selected) notFound();
  return <ValuationWorkspace key={selected.id} example={selected} choices={bundle.examples.map(({ id, label }) => ({ id, label }))} />;
}
