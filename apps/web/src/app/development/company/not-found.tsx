import WorkbenchShell from "@/components/WorkbenchShell";

export default function OverviewNotFound() {
  return <WorkbenchShell active="company" fictional><main id="main-content" tabIndex={-1} className="setup-page"><p className="eyebrow">COMPANY OVERVIEW</p><h1>N/A</h1><form action="/development/company" method="get"><button type="submit" className="primary-link">Choose a saved company ↗</button></form></main></WorkbenchShell>;
}
