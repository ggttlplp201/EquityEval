import Link from "next/link";
export default function SectorsPage() {
  return <main className="setup-page">
    <Link href="/sectors" className="brand"><span className="brand-mark">E</span> EquityEval <span className="brand-caption">RESEARCH WORKBENCH</span></Link>
    <div className="eyebrow">SECTOR EXPLORER</div>
    <h1>A broader view.<br /><span>Grounded in the sources.</span></h1>
    <p className="setup-intro">Compare valuation, growth and the companies behind each sector. Production data is not configured yet.</p>
    <div className="setup-status"><span className="status-dot" /> DATA PREREQUISITES REQUIRED</div>
    <ol className="prerequisite-list">
      <li><strong>A complete, dated issuer universe</strong><span>Independent of available ratios, with share classes and depositary receipts deduplicated.</span></li>
      <li><strong>Licensed taxonomy and membership history</strong><span>Approved provider, effective assignments and known-at dates. Unknown assignments remain visible.</span></li>
      <li><strong>Comparable financial and capitalization snapshots</strong><span>Supported USD TTM facts, common-shareholder earnings, all-class capitalization, freshness and source evidence.</span></li>
      <li><strong>Reviewed snapshot storage and API</strong><span>Immutable inputs and results, source revisions, authorized refresh and precise provenance.</span></li>
    </ol>
    <Link className="primary-link" href="/development/sectors">Explore the fictional demonstration <span aria-hidden="true">↗</span></Link>
    <p className="small muted">The demonstration uses invented companies and financial inputs. It is not current market data.</p>
  </main>;
}
