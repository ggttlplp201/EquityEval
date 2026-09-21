import Link from "next/link";
import WorkbenchShell from "@/components/WorkbenchShell";

export default function CompanySnapshotNotFound() {
  return <WorkbenchShell active="company" fictional>
    <main id="main-content" tabIndex={-1} className="setup-page">
      <p className="eyebrow">COMPANY SNAPSHOT UNAVAILABLE</p>
      <h1>This selection has no saved result.</h1>
      <p className="setup-intro">The company or evaluation date is not in the fictional demonstration, or the link specifies more than one selection. No other company’s values have been substituted.</p>
      <Link className="primary-link" href="/development/company">Choose an available company ↗</Link>
    </main>
  </WorkbenchShell>;
}
