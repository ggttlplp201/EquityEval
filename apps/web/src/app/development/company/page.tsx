import { readFile } from "node:fs/promises";
import path from "node:path";
import { gunzip } from "node:zlib";
import { promisify } from "node:util";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import CompanyWorkspace from "@/features/company/CompanyWorkspace";
import type { CompanyBundle } from "@/features/company/types";

export const metadata: Metadata = { title: "Company Fundamentals · EquityEval" };

export default async function CompanyPage({ searchParams }: {
  searchParams: Promise<{ company?: string | string[]; asOf?: string | string[] }>;
}) {
  const query = await searchParams;
  if (Array.isArray(query.company) || Array.isArray(query.asOf)) notFound();
  const file = path.join(process.cwd(), "src/features/company/fixture.json.gz");
  const bytes = await promisify(gunzip)(await readFile(file));
  const bundle = JSON.parse(bytes.toString("utf8")) as CompanyBundle;
  if (bundle.fictional !== true) throw new Error("Company development requires an explicitly fictional fixture.");
  const companyId = query.company ?? bundle.context.defaultCompanyId;
  const selectedAsOf = query.asOf ?? bundle.context.defaultAsOf;
  const company = bundle.companies.find((item) => item.id === companyId);
  if (!company || !bundle.views[`${selectedAsOf}|${companyId}`]) notFound();
  // Send only this issuer and evidence available by the selected snapshot date.
  // No production symbol resolver, provider fetch or public API is implied.
  const views = Object.values(bundle.views).filter((view) => view.companyId === companyId && view.asOf <= selectedAsOf);
  const detailIds = new Set(views.map((view) => view.detailId));
  const details = Object.fromEntries(Object.entries(bundle.details).filter(([id]) => detailIds.has(id)));
  return <CompanyWorkspace data={{ fictional: true, context: bundle.context, companies: bundle.companies, metrics: bundle.metrics, company, selectedAsOf, views, details }} />;
}
