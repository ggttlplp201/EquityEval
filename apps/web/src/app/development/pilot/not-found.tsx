import Link from "next/link";
import WorkbenchShell from "@/components/WorkbenchShell";

export default function PilotSelectionNotFound() {
  return <WorkbenchShell active="pilot">
    <main id="main-content" tabIndex={-1} className="setup-page">
      <p className="eyebrow">PILOT SELECTION UNAVAILABLE</p>
      <h1>This company is outside the pilot selection.</h1>
      <p className="setup-intro">Choose one of CRCL, MSTR, COIN, HOOD, USAR, MP or GOOGL. A link must specify exactly one company. No other company’s financial values have been substituted.</p>
      <Link className="primary-link" href="/development/pilot">Return to the real-data pilot ↗</Link>
    </main>
  </WorkbenchShell>;
}
