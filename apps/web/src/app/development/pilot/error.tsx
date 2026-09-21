"use client";

import Link from "next/link";
import WorkbenchShell from "@/components/WorkbenchShell";

export default function PilotError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <WorkbenchShell active="pilot">
    <main id="main-content" tabIndex={-1} className="setup-page" role="alert">
      <p className="eyebrow">ARCHIVED EVIDENCE UNAVAILABLE</p>
      <h1>The pilot snapshot could not load.</h1>
      <p className="setup-intro">No financial values are shown without their source records. Retry the saved snapshot; a retry here does not fetch live data or replace missing observations.</p>
      <button type="button" className="primary-link" onClick={reset}>Retry saved snapshot</button>
      <p><Link href="/help#real-source-pilot">Read the pilot guide ↗</Link></p>
    </main>
  </WorkbenchShell>;
}
