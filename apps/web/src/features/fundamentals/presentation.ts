import type { FundamentalsPayload, PublicMetric, PublicObservation } from "@equity/schema/types/fundamentals";
import { number } from "../valuation/presentation";

export const statuses: Record<PublicMetric["status"], string> = {
  valid: "Valid", not_meaningful: "N/M", missing: "Missing", invalid: "Invalid",
  stale: "Stale", unsupported: "Unsupported", inapplicable: "Inapplicable",
};
export function metricDisplay(metric: Pick<PublicMetric, "status" | "value" | "unit">): string {
  if (metric.value === null) return metric.status === "not_meaningful" ? "N/M" : "N/A";
  return `${number(metric.value, metric.unit === "fraction")}${metric.unit === "multiple" ? "×" : ""}`;
}
export const metrics: Record<string, { label: string; definition: string }> = {
  "reported.revenue": { label: "Revenue", definition: "Reported sales for the selected financial period." },
  revenue_growth_yoy: { label: "Revenue growth · YoY", definition: "Change relative to the comparable prior-year period, divided by positive prior revenue." },
  gross_margin: { label: "Gross margin", definition: "Reported gross profit divided by revenue." },
  operating_margin: { label: "Operating margin", definition: "Operating income divided by revenue." },
  net_margin_consolidated: { label: "Net margin", definition: "Consolidated net income divided by revenue." },
  "reported.cash_from_operating_activities": { label: "Operating cash flow", definition: "Reported cash from operating activities for the selected period." },
  free_cash_flow_ppe: { label: "Free cash flow · PPE", definition: "Operating cash flow less cash purchases of property, plant and equipment. This differs from FCFF in Reverse DCF." },
  free_cash_flow_margin_ppe: { label: "Free cash flow margin", definition: "PPE free cash flow divided by revenue." },
  "reported.current_assets": { label: "Current assets", definition: "Reported current assets at the balance-sheet date." },
  "reported.current_liabilities": { label: "Current liabilities", definition: "Reported current liabilities at the balance-sheet date." },
  current_ratio: { label: "Current ratio", definition: "Current assets divided by positive current liabilities." },
  net_working_capital: { label: "Net working capital", definition: "Current assets less current liabilities; distinct from operating working capital." },
  trailing_pe: { label: "Trailing P/E", definition: "Price relative to compatible trailing earnings per share. This saved S6a example has no supported multiple." },
  return_on_assets: { label: "Return on assets", definition: "Consolidated net income divided by the average of compatible opening and closing total assets." },
};
export const sections = [
  { title: "Growth", ids: ["reported.revenue", "revenue_growth_yoy"] },
  { title: "Profitability", ids: ["gross_margin", "operating_margin", "net_margin_consolidated"] },
  { title: "Cash generation", ids: ["reported.cash_from_operating_activities", "free_cash_flow_ppe", "free_cash_flow_margin_ppe"] },
  { title: "Balance sheet", ids: ["reported.current_assets", "reported.current_liabilities", "current_ratio", "net_working_capital"] },
  { title: "Valuation", ids: ["trailing_pe"] },
  { title: "Returns on capital", ids: ["return_on_assets"] },
];
export function savedNotes(payload: Pick<FundamentalsPayload, "review_items" | "observations">): PublicObservation[] {
  const topics = new Set<string>();
  return [...payload.review_items, ...payload.observations].filter((item) => {
    if (topics.has(item.topic)) return false;
    topics.add(item.topic); return true;
  }).slice(0, 3);
}

// Coordinate labels only: grouping equal supplied positions does not calculate quartiles.
export function chartLabels(positions: readonly string[]): { x: string; label: string }[] {
  const labels = new Map<string, string[]>();
  positions.forEach((x, index) => labels.set(x, [...(labels.get(x) ?? []), ["P25", "Median", "P75"][index]]));
  return [...labels].map(([x, names]) => ({ x, label: names.join(" = ") }));
}
