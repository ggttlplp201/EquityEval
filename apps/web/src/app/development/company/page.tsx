import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { gunzip } from "node:zlib";
import { promisify } from "node:util";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import CompanyWorkspace from "@/features/company/CompanyWorkspace";
import type { CompanyBundle } from "@/features/company/types";

import { resolveSelection } from "@/features/company/selection";
import { historyEvidence, overviewEvidence, type OverviewManifest } from "@/features/company/overview";

export const metadata: Metadata = { title: "Company Overview · EquityEval" };

export default async function CompanyPage({ searchParams }: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const file = path.join(process.cwd(), "src/features/company/fixture.json.gz");
  const raw = await readFile(file);
  const bytes = await promisify(gunzip)(raw);
  const bundle = JSON.parse(bytes.toString("utf8")) as CompanyBundle;
  if (bundle.fictional !== true) throw new Error("Company development requires an explicitly fictional fixture.");
  const selected = resolveSelection(bundle, query);
  if (!selected) notFound();
  const { company, view } = selected;
  const companyId = company.id;
  const selectedAsOf = view.asOf;
  const manifest = JSON.parse(await readFile(path.join(process.cwd(), "src/features/company/overview.json"), "utf8")) as OverviewManifest;
  if (manifest.fictional !== true || manifest.version !== "s8d-metadata-v1") throw new Error("Invalid Overview manifest");
  const expectedFiles = ["company/fixture.json.gz", "financials/fixture.json", "fundamentals/fixture.json", "valuation/fixture.json"];
  if (Object.keys(manifest.files).sort().join() !== expectedFiles.sort().join()) throw new Error("Invalid Overview file roster");
  await Promise.all(expectedFiles.map(async (relative) => {
    let contents: Buffer;
    try { contents = relative === "company/fixture.json.gz" ? raw : await readFile(path.join(process.cwd(), "src/features", relative)); }
    catch (error) { if ((error as NodeJS.ErrnoException).code === "ENOENT" && manifest.files[relative] === null) return; throw error; }
    if (createHash("sha256").update(contents).digest("hex") !== manifest.files[relative]) throw new Error("Stale Overview manifest");
  }));
  const overview = overviewEvidence(manifest, view);
  // Send only this issuer and evidence available by the selected snapshot date.
  // No production symbol resolver, provider fetch or public API is implied.
  const views = Object.values(bundle.views).filter((view) => view.companyId === companyId && view.asOf <= selectedAsOf);
  const detailIds = new Set(views.map((view) => view.detailId));
  const details = Object.fromEntries(Object.entries(bundle.details).filter(([id]) => detailIds.has(id)));
  details[overview.data.detailId] = overview.detail;
  for (const years of ["3", "5", "10"]) details[`history|${view.id}|${years}`] = historyEvidence(view, years, bundle.details[view.detailId]);
  return <CompanyWorkspace data={{ fictional: true, context: bundle.context, companies: bundle.companies, metrics: bundle.metrics, company, selectedAsOf, views, details, overview: overview.data }} />;
}
