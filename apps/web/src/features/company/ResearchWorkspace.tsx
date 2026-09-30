import Link from "next/link";
import type { OverviewData } from "./overview";
import styles from "./company.module.css";

export default function ResearchWorkspace({ data, onDetail }: { data: OverviewData; onDetail: (id: string) => void }) {
  return <section aria-labelledby="workspace-title" className={styles.workspace}>
    <div className={styles.sectionHeading}><h2 id="workspace-title">Research workspace</h2><button className="text-button" onClick={() => onDetail(data.detailId)}>Inspect linkage evidence ↗</button></div>
    <div className={styles.workspaceCounts}>{Object.entries(data.counts).map(([label, count]) => <button key={label} className="text-button" data-linkage-count={label} onClick={() => onDetail(data.detailId)}>{label}: {count}</button>)}</div>
    <div className={styles.workspaceGrid}>{data.cards.map((card) => <article key={card.id} data-workspace={card.id} data-linkage={card.status}>
      <h3>{card.title}</h3><p>{card.statusLabel}</p><p>{card.name ?? "N/A"}</p>
      <button className="text-button" aria-label={`${card.title} evaluation date. Inspect linkage evidence`} onClick={() => onDetail(data.detailId)}>{card.asOf ?? "N/A"} ↗</button>
      <p>{card.navigationLabel}</p>
      {card.href ? <Link href={card.href} prefetch={false} aria-current={card.id === "overview" ? "page" : undefined}>Open {card.title} ↗</Link> : <span>N/A</span>}
    </article>)}</div>
  </section>;
}
