import { readFile } from "node:fs/promises";
import path from "node:path";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import FundamentalsWorkspace from "@/features/fundamentals/FundamentalsWorkspace";
import { resolveSelection } from "@/features/fundamentals/selection";
import type { Bundle } from "@/features/fundamentals/types";

export const metadata: Metadata = { title: "Fundamentals · EquityEval" };
export default async function FundamentalsPage({ searchParams }: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  if (Object.values(query).some(Array.isArray)) notFound();
  const bundle = JSON.parse(await readFile(path.join(process.cwd(), "src/features/fundamentals/fixture.json"), "utf8")) as Bundle;
  if (bundle.fictional !== true) throw new Error("Fictional fundamentals fixture required");
  const selected = resolveSelection(bundle, query);
  if (!selected) notFound();
  return <FundamentalsWorkspace key={selected.snapshot_id} saved={selected} examples={bundle.examples} label={bundle.label} />;
}
