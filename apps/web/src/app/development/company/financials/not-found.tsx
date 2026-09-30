import Link from "next/link";
import WorkbenchShell from "@/components/WorkbenchShell";

export default function FinancialsNotFound() {
  return <WorkbenchShell active="financials" fictional><main id="main-content" tabIndex={-1} className="setup-page"><p className="eyebrow">FINANCIALS</p><h1>N/A</h1><Link href="/development/company/financials" className="primary-link">Choose a saved edition ↗</Link></main></WorkbenchShell>;
}
