import Link from "next/link";
import type { ReactNode } from "react";

type Destination = "sectors" | "company" | "pilot" | "news" | "help";
const destinations: { id: Destination; href: string; label: string }[] = [
  { id: "sectors", href: "/development/sectors", label: "Sector Explorer" },
  { id: "company", href: "/development/company", label: "Company" },
  { id: "pilot", href: "/development/pilot", label: "Real-data pilot" },
  { id: "news", href: "/development/news", label: "News & calendar" },
  { id: "help", href: "/help", label: "Help" },
];

export default function WorkbenchShell({ active, fictional = false, children }: {
  active: Destination; fictional?: boolean; children: ReactNode;
}) {
  const banner = active === "news"
    ? { label: "NOT MONITORING", text: "Sources, collection, assessments and alert delivery are unconfigured" }
    : active === "help"
      ? { label: "USER GUIDE", text: "Development edition · current and planned workflows are distinguished" }
      : { label: fictional ? "FICTIONAL DATA" : "DEVELOPMENT", text: "Offline demonstration · invented companies and financial inputs · no market conclusions" };
  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    {active !== "pilot" ? <div className="fictional-banner"><strong>{banner.label}</strong><span>{banner.text}</span><Link href="/sectors">Production prerequisites ↗</Link></div> : null}
    <header className="app-header">
      <Link href="/development/sectors" prefetch={false} className="brand"><span className="brand-mark">E</span> EquityEval</Link>
      <nav aria-label="Main">{destinations.map((item) => <Link key={item.id} href={item.href} prefetch={false} className={active === item.id ? "nav-active" : undefined} aria-current={active === item.id ? "page" : undefined}>{item.label}</Link>)}<Link href="/sectors">Data readiness</Link></nav>
      <span className="local-indicator"><span /> {active === "news" ? "Monitoring inactive" : active === "pilot" ? "Saved SEC evidence" : "Local development"}</span>
    </header>
    {children}
  </div>;
}
