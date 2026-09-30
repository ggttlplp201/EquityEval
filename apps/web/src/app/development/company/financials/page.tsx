import { readFile } from "node:fs/promises";
import path from "node:path";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import FinancialsWorkspace from "@/features/financials/FinancialsWorkspace";
import { resolveSelection } from "@/features/financials/selection";
import type { Bundle } from "@/features/financials/types";

export const metadata: Metadata = { title: "Financials · EquityEval" };
export default async function FinancialsPage({ searchParams }: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const bundle = JSON.parse(await readFile(path.join(process.cwd(), "src/features/financials/fixture.json"), "utf8")) as Bundle;
  if (bundle.fictional !== true) throw new Error("Fictional financials fixture required");
  const saved = resolveSelection(bundle, query);
  if (!saved) notFound();
  return <FinancialsWorkspace key={saved.snapshot_id} saved={saved} choices={bundle.choices} />;
}
