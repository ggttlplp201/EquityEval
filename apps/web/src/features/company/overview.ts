import type { EvidenceDetail } from "@/features/sectors/types";
import type { CompanyView } from "./types";

/** Local checked presentation metadata only; not a shared financial API. */
export interface WorkspaceCard {
  id: string; title: string; status: "ready" | "compatible" | "separate" | "unavailable";
  statusLabel: string; name: string | null; asOf: string | null;
  reasons: string[]; href: string | null; navigationLabel: string;
}
export interface OverviewEntry {
  identity: Record<string, unknown>;
  cards: WorkspaceCard[];
  counts: Record<string, number>;
}
export interface OverviewManifest {
  version: string; fictional: true; files: Record<string, string | null>; method: string;
  destinations: Record<string, Record<string, unknown>>;
  entries: Record<string, OverviewEntry>;
}
export interface OverviewData extends OverviewEntry { detailId: string }

/** Project exact checked metadata into existing evidence drawer rows. */
export function overviewEvidence(manifest: OverviewManifest, view: CompanyView) {
  const entry = manifest.entries[view.id];
  if (!entry || entry.identity.view_id !== view.id || entry.identity.snapshot_id !== view.snapshotId || entry.identity.issuer_id !== view.companyId || entry.identity.as_of !== view.asOf) throw new Error("Overview manifest selection mismatch");
  const detailId = `overview|${view.id}`;
  const detail: EvidenceDetail = {
    title: "Research workspace linkage", subtitle: manifest.method,
    sections: [
      { heading: "Selected Overview identity", rows: Object.entries(entry.identity).map(([label, value]) => ({ label, value: value == null ? "N/A" : typeof value === "string" ? value : JSON.stringify(value, null, 2) })) },
      { heading: "Saved linkage counts and decisions", rows: [{ label: "Counts", value: JSON.stringify(entry.counts, null, 2) }, { label: "Workspace roster", value: JSON.stringify(entry.cards, null, 2) }] },
      ...entry.cards.filter((card) => card.id !== "overview").map((card) => ({ heading: card.title, rows: [
        { label: "Linkage", value: card.statusLabel }, { label: "Reasons", value: card.reasons.join("\n") || "N/A" },
        { label: "Exact destination metadata", value: manifest.destinations[card.id] ? JSON.stringify(manifest.destinations[card.id], null, 2) : "N/A" },
      ] })),
      { heading: "Checked source files", rows: Object.entries(manifest.files).map(([label, value]) => ({ label, value: value ?? "N/A" })) },
    ], sources: [],
  };
  return { data: { ...entry, detailId }, detail };
}

export function historyEvidence(view: CompanyView, years: string, source: EvidenceDetail): EvidenceDetail {
  const history = view.history[years];
  return { ...source, title: "Saved history coverage", sections: [
    { heading: "Exact history selection", rows: [
      { label: "View ID", value: view.id }, { label: "Snapshot ID", value: view.snapshotId },
      { label: "Requested years", value: years },
      ...Object.entries(history).filter(([key]) => key !== "charts").map(([label, value]) => ({ label, value: typeof value === "string" ? value : JSON.stringify(value, null, 2) })),
    ] }, ...source.sections,
  ] };
}
