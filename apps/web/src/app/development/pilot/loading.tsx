import WorkbenchShell from "@/components/WorkbenchShell";

export default function PilotLoading() {
  return <WorkbenchShell active="pilot">
    <main id="main-content" tabIndex={-1} className="setup-page" aria-busy="true">
      <p className="eyebrow">ARCHIVED EVIDENCE</p>
      <h1>Opening the selected pilot snapshot…</h1>
      <p className="setup-intro">Waiting for its source observations, dates and coverage limitations. No live source request is being made.</p>
    </main>
  </WorkbenchShell>;
}
