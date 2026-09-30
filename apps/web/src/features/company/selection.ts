import type { CompanyBundle } from "./types";

/** Resolve exactly one saved issuer/view; malformed URLs never become defaults. */
export function resolveSelection(bundle: CompanyBundle, query: Record<string, string | string[] | undefined>) {
  if (Object.keys(query).some((key) => !["company", "asOf"].includes(key)) || Object.values(query).some(Array.isArray)) return null;
  const companyId = query.company ?? bundle.context.defaultCompanyId;
  const asOf = query.asOf ?? bundle.context.defaultAsOf;
  if (new Set(bundle.context.asOfDates).size !== bundle.context.asOfDates.length || !bundle.context.asOfDates.includes(String(asOf))) return null;
  const companies = bundle.companies.filter((item) => item.id === companyId);
  const views = Object.values(bundle.views).filter((item) => item.companyId === companyId && item.asOf === asOf);
  if (companies.length !== 1 || views.length !== 1 || bundle.views[`${asOf}|${companyId}`] !== views[0]) return null;
  return { company: companies[0], view: views[0] };
}
