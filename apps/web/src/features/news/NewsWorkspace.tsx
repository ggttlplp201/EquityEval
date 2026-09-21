"use client";

import Link from "next/link";
import { useState } from "react";
import styles from "./news.module.css";

type Section = "calendar" | "topics" | "health";
type TopicCategory = "regulation" | "products" | "relationships" | "capital" | "operations";
interface CoverageTopic { title: string; category: TopicCategory; question: string }
interface PilotCompany { ticker: string; name: string; scope: string; topics: CoverageTopic[] }

// Planning catalog only: these are not collected stories, saved topics or active subscriptions.
const PILOT: PilotCompany[] = [
  { ticker: "CRCL", name: "Circle", scope: "Stablecoin, reserve and platform economics", topics: [
    { title: "Stablecoin rules and the CLARITY Act", category: "regulation", question: "Verify the exact legal stage and affected business activity; a proposal is not an enacted rule." },
    { title: "Open USD and competing stablecoin products", category: "products", question: "Check product identity, adoption evidence and distribution terms before inferring a competitive effect." },
    { title: "Arc and payment-network developments", category: "products", question: "Separate an announcement or testnet from production use and evidenced fee revenue." },
    { title: "Reserve economics and distribution partners", category: "relationships", question: "Trace reserve income, distribution costs and retained revenue separately; holder reserves are not corporate cash." },
  ] },
  { ticker: "MSTR", name: "Strategy", scope: "Bitcoin treasury and operating software, separately", topics: [
    { title: "Treasury transactions and financing", category: "capital", question: "Separate holdings, fair-value changes, senior claims and common-share dilution; a financing announcement is not software growth." },
    { title: "Enterprise analytics software", category: "products", question: "Look for evidence of demand, customer contracts and operating performance distinct from treasury effects." },
    { title: "Digital-asset accounting and regulation", category: "regulation", question: "Verify which assets, entities and periods a change affects. MSTR is not a Bitcoin-mining profile." },
  ] },
  { ticker: "COIN", name: "Coinbase", scope: "Transaction, subscription and service activity", topics: [
    { title: "Exchange, custody and stablecoin rules", category: "regulation", question: "Identify the product, jurisdiction and legal stage; distinguish customer balances from corporate assets." },
    { title: "Trading products, fees and competition", category: "products", question: "Check volume, fee definitions and product mix separately; token prices and activity are not company revenue." },
    { title: "Stablecoin and platform partnerships", category: "relationships", question: "Look for actual contractual economics and dated revenue evidence, including offsetting costs." },
  ] },
  { ticker: "HOOD", name: "Robinhood", scope: "Brokerage, net-interest and subscription activity", topics: [
    { title: "Brokerage and market-structure rules", category: "regulation", question: "Identify affected transaction or lending activity and distinguish proposals from effective requirements." },
    { title: "Products, pricing and subscriptions", category: "products", question: "Separate engagement, funded customers, subscriptions and revenue; confirm each metric's definition." },
    { title: "Acquisitions and customer-scope changes", category: "operations", question: "Preserve acquisition dates and KPI boundaries before interpreting a change as organic growth." },
    { title: "Interest income and regulated capital", category: "capital", question: "Inspect the balance and funding channels separately; customer assets are not unrestricted corporate cash." },
  ] },
  { ticker: "USAR", name: "USA Rare Earth", scope: "Minerals, processing and magnets by project", topics: [
    { title: "LCM, Stillwater, Round Top and Serra Verde", category: "operations", question: "Verify each project's dated operating, development, ramp or integration stage; do not apply one lifecycle to the whole company." },
    { title: "Permits, trade rules and public support", category: "regulation", question: "Separate approvals, conditions and implementation dates; an announced program is not received funding." },
    { title: "Project funding and ownership changes", category: "capital", question: "Check commitments, conditions, acquisition scope and dilution; planned capacity is not current sales." },
    { title: "Customer qualification and offtake", category: "relationships", question: "Distinguish qualification, signed terms and actual shipments; retain missing commercial evidence." },
  ] },
  { ticker: "MP", name: "MP Materials", scope: "Materials and Magnetics with distinct project stages", topics: [
    { title: "Materials output and downstream ramp", category: "operations", question: "Separate extraction, processing, precursor sales and permanent-magnet production; planned capacity is not shipped output." },
    { title: "Price protection and trade policy", category: "regulation", question: "Inspect exact agreement terms and accounting treatment; price-support income is not automatically product revenue." },
    { title: "Customer contracts and qualification", category: "relationships", question: "Check product specifications, contract scope and qualification evidence before assigning a demand effect." },
    { title: "Project investment and funding", category: "capital", question: "Separate operating costs, project commitments and financing; commodity prices alone do not establish sustainable earnings." },
  ] },
  { ticker: "GOOGL", name: "Alphabet", scope: "Services, Cloud and Other Bets with shared costs", topics: [
    { title: "Search, advertising and AI competition", category: "products", question: "Link product announcements to evidenced monetization or costs; usage and revenue are different measures." },
    { title: "Cloud customers, partners and capacity", category: "relationships", question: "Distinguish backlog, contracted commitments and recognized revenue, including investment needed to serve demand." },
    { title: "Antitrust, privacy and distribution rules", category: "regulation", question: "Verify the affected business line, legal stage and implementation terms rather than infer an immediate earnings change." },
    { title: "Capital spending and segment changes", category: "operations", question: "Keep Services, Cloud, Other Bets and shared costs separate; GOOGL Class A is not interchangeable with GOOG Class C." },
  ] },
];

const CATEGORIES: { id: TopicCategory; label: string }[] = [
  { id: "regulation", label: "Regulation & policy" },
  { id: "products", label: "Products & competition" },
  { id: "relationships", label: "Partners, customers & suppliers" },
  { id: "capital", label: "Funding & capital" },
  { id: "operations", label: "Operations & milestones" },
];
const SECTIONS: { id: Section; label: string }[] = [
  { id: "calendar", label: "Calendar" },
  { id: "topics", label: "Stock topics" },
  { id: "health", label: "Monitor health" },
];
const MACRO_COVERAGE = [
  { title: "CPI", source: "BLS schedule and release", detail: "Consumer prices: distinguish headline and core, monthly and yearly changes, seasonal basis and revisions." },
  { title: "PPI", source: "BLS schedule and release", detail: "Producer prices: retain the exact measure, reference period and revision vintage." },
  { title: "FOMC statement", source: "Federal Reserve calendar and statement", detail: "A separate release stage for the policy decision and statement text." },
  { title: "FOMC press conference", source: "Federal Reserve event schedule", detail: "A separately verified time and event; do not reuse the statement's release time." },
  { title: "Economic projections", source: "Federal Reserve scheduled projections", detail: "Included only when the official schedule confirms projections; not assumed for every meeting." },
  { title: "FOMC minutes", source: "Federal Reserve minutes schedule", detail: "A later publication with its own release time and meeting reference." },
];

function ConfigurationLinks() {
  return <div className={styles.links}><Link href="/sectors">Review data readiness ↗</Link><Link href="/help">Open the user guide ↗</Link></div>;
}

function CalendarView({ scope }: { scope: string }) {
  return <>
    <section className={styles.panel} aria-labelledby="calendar-title">
      <div className={styles.panelHeading}><div><p className="eyebrow">US ECONOMIC CALENDAR</p><h2 id="calendar-title">Shared events, company-specific context</h2></div><span className={styles.status}>Schedule unconfigured</span></div>
      <div className={styles.emptyState}>
        <span className={styles.emptyIcon} aria-hidden="true">◷</span>
        <h3>No verified event schedule is available</h3>
        <p>No calendar source is connected here. Upcoming dates, release times and heads-up alerts cannot be shown yet. This is a coverage gap, not a claim that no events are coming.</p>
        <p className={styles.scopeNote}>Selected context: {scope}. US macro coverage is shared across the watchlist; future assessments must explain each company’s own exposure.</p>
        <ConfigurationLinks />
      </div>
    </section>
    <section className={styles.panel} aria-labelledby="macro-coverage-title">
      <div className={styles.panelHeading}><div><p className="eyebrow">PROPOSED COVERAGE · NOT SCHEDULED EVENTS</p><h2 id="macro-coverage-title">What the calendar will follow</h2></div></div>
      <div className={styles.macroGrid}>{MACRO_COVERAGE.map((event) => <article className={styles.coverageCard} key={event.title}><h3>{event.title}</h3><p>{event.detail}</p><span className={styles.sourceNeed}>Required: {event.source}</span></article>)}</div>
      <p className={styles.footnote}>Payrolls and PCE remain planned source additions after adapter checks. No release date or time is inferred from a recurring weekday pattern.</p>
    </section>
    <div className={styles.twoColumns}>
      <section className={styles.panel} aria-labelledby="release-states-title"><p className="eyebrow">DISTINCT EVENT STATES</p><h2 id="release-states-title">Before and after a release</h2><dl className={styles.definitionList}><div><dt>Heads-up</dt><dd>A verified future schedule; configurable lead times remain unconfigured.</dd></div><div><dt>Released</dt><dd>Published actual, timestamped consensus if available, and prior value remain separate. Prior is not consensus.</dd></div><div><dt>Correction</dt><dd>A new source revision preserves the original figure and timestamp.</dd></div></dl></section>
      <section className={`${styles.panel} ${styles.aside}`} aria-labelledby="time-title"><p className="eyebrow">TIME & EVIDENCE</p><h2 id="time-title">Unconfirmed stays unconfirmed</h2><p>A sourced release time and timezone must be verified before local conversion or hour-specific alerts. A date-only schedule cannot supply a precise release time.</p><p>Reschedules and cancellations will retain the original schedule history. Consensus and observed price reactions remain unavailable until compatible sources exist.</p></section>
    </div>
  </>;
}

function TopicsView({ selectedCompany, category, setCategory, clearFilters }: { selectedCompany: string; category: TopicCategory | "all"; setCategory: (value: TopicCategory | "all") => void; clearFilters: () => void }) {
  const companies = PILOT.filter((company) => selectedCompany === "all" || company.ticker === selectedCompany)
    .map((company) => ({ ...company, topics: company.topics.filter((topic) => category === "all" || topic.category === category) }))
    .filter((company) => company.topics.length > 0);
  return <>
    <section className={styles.panel} aria-labelledby="topics-title">
      <div className={styles.panelHeading}><div><p className="eyebrow">PROPOSED COVERAGE CATALOG</p><h2 id="topics-title">Follow the business, beyond the ticker</h2></div><label className={styles.filter}><span>Topic category</span><select value={category} onChange={(event) => setCategory(event.target.value as TopicCategory | "all")}><option value="all">All topic categories</option>{CATEGORIES.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label></div>
      <p className={styles.intro}>These are starting areas for the seven-company pilot, not retrieved stories or active monitoring topics. A future discovery process must verify relationships and find new relevant developments even when neither the ticker nor a known topic appears.</p>
      <p className={styles.footnote}>Changing a filter only changes this view. Following, editing, muting and saving topics are not connected yet. No monitoring subscriptions are changed.</p>
      <div className={styles.topicResults} aria-live="polite" aria-atomic="true"><span>{selectedCompany === "all" ? "All pilot companies" : selectedCompany} · {category === "all" ? "All topic categories" : CATEGORIES.find((item) => item.id === category)?.label}</span><span className={styles.status}>Not monitored</span></div>
      {companies.length > 0 ? <div className={styles.companyTopics}>{companies.map((company) => <article key={company.ticker} className={styles.companyCard}><header><div><span className={styles.ticker}>{company.ticker}</span><h3>{company.name}</h3></div><span className={styles.candidate}>Planning context</span></header><p className={styles.companyScope}>{company.scope}</p><ul>{company.topics.map((topic) => <li key={topic.title}><span className={styles.category}>{CATEGORIES.find((item) => item.id === topic.category)?.label}</span><h4>{topic.title}</h4><p>{topic.question}</p></li>)}</ul></article>)}</div> : <div className={styles.emptyState}><h3>No proposed topics match these filters</h3><p>This filters the planning catalog, not live news. It does not establish that this company has no relevant developments.</p><button className={styles.secondaryButton} onClick={clearFilters}>Clear filters</button></div>}
    </section>
    <section className={`${styles.panel} ${styles.aside}`} aria-labelledby="assessment-title"><p className="eyebrow">IMPACT ASSESSMENTS · NOT AVAILABLE YET</p><h2 id="assessment-title">An explanation needs evidence</h2><p className={styles.intro}>No impact assessment has been produced here. A future assessment will keep the following parts distinct and remain useful when the evidence cannot support a direction.</p><div className={styles.assessmentGrid}><div><h3>Verified facts</h3><p>Exact passages, source identity, publication and retrieval times, legal or product stage, and dated business metrics.</p></div><div><h3>Conditional interpretation</h3><p>Named business driver, possible favorable, adverse or offsetting channels, horizon, and uncertainty. Source reliability is separate from confidence in the explanation.</p></div><div><h3>What could change the view</h3><p>Counterevidence, missing metrics, alternative explanations and the next review condition. Revisions retain the previous assessment.</p></div></div><p className={styles.footnote}>Price movement does not prove causation. No numerical valuation impact is available without an applicable tested model and confirmed assumptions. News will not overwrite saved facts, assumptions or research.</p></section>
    <ConfigurationLinks />
  </>;
}

function HealthView() {
  return <>
    <section aria-labelledby="health-title"><div className={styles.sectionHeading}><p className="eyebrow">MONITOR HEALTH</p><h2 id="health-title">Collection, assessment and delivery are separate</h2><p>No monitoring service is connected to this development workspace. These are configuration limits, not a healthy or empty news feed.</p></div><div className={styles.healthGrid}>
      <article className={styles.panel}><span className={styles.status}>Unconfigured</span><h3>Collection</h3><p className={styles.cardDescription}>Are sources being checked?</p><dl className={styles.definitionList}><div><dt>News and calendar sources</dt><dd>Not connected</dd></div><div><dt>Collection worker</dt><dd>Not configured</dd></div><div><dt>Effective cadence</dt><dd>Not scheduled</dd></div><div><dt>Last successful check</dt><dd>Unavailable — no collection run</dd></div><div><dt>Source coverage and lag</dt><dd>Not measured</dd></div></dl></article>
      <article className={styles.panel}><span className={styles.status}>Unconfigured</span><h3>Assessment</h3><p className={styles.cardDescription}>Has the evidence been reviewed?</p><dl className={styles.definitionList}><div><dt>Assessment worker</dt><dd>Not configured</dd></div><div><dt>Latest completed coverage</dt><dd>Unavailable</dd></div><div><dt>Discovery and assessment backlog</dt><dd>Unavailable — no queue connected</dd></div><div><dt>Published assessments</dt><dd>None produced here</dd></div></dl><p className={styles.footnote}>A successful fetch alone will not establish that relevance discovery or assessment has completed.</p></article>
      <article className={styles.panel}><span className={styles.status}>Unconfigured</span><h3>Host & delivery</h3><p className={styles.cardDescription}>Can monitoring continue and alerts arrive?</p><dl className={styles.definitionList}><div><dt>Background runtime</dt><dd>Not configured</dd></div><div><dt>Host availability</dt><dd>Not checked</dd></div><div><dt>Quiet hours and lead times</dt><dd>Not configured</dd></div><div><dt>Alert delivery</dt><dd>Not running</dd></div></dl><p className={styles.footnote}>Local collection cannot continue while its worker is stopped or the laptop sleeps. This page does not claim always-on monitoring.</p></article>
    </div></section>
    <section className={styles.panel} aria-labelledby="channels-title"><div className={styles.panelHeading}><div><p className="eyebrow">ALL THREE REQUESTED CHANNELS</p><h2 id="channels-title">Delivery needs its own setup</h2></div></div><div className={styles.channelGrid}>
      <article className={styles.coverageCard}><span className={styles.status}>Unconfigured</span><h3>In-app inbox</h3><p>No alert history or delivery service is connected. This workspace is not a running inbox.</p></article>
      <article className={styles.coverageCard}><span className={styles.status}>Unconfigured</span><h3>Desktop notifications</h3><p>Permission has not been checked or requested. A future setup must confirm the OS permission and delivery state.</p></article>
      <article className={styles.coverageCard}><span className={styles.status}>Unconfigured</span><h3>Email</h3><p>No sender or verified alert recipient is configured here. An SEC contact address does not enroll anyone for alerts.</p></article>
    </div><p className={styles.footnote}>No alert has been sent from this workspace. Future delivery states will distinguish queued, attempted, acknowledged, failed and disabled; acknowledgement is not proof of reading.</p></section>
    <section className={`${styles.panel} ${styles.aside}`} aria-labelledby="recovery-title"><p className="eyebrow">BEFORE MONITORING STARTS</p><h2 id="recovery-title">Coverage, recovery and your controls</h2><div className={styles.assessmentGrid}><div><h3>Source boundaries</h3><p>Approved sources, permitted use, budgets and checked windows determine coverage. Monitoring cannot claim the whole internet.</p></div><div><h3>Catch-up without duplicate alerts</h3><p>Recovery must retain original publication times and label delayed discoveries. Baseline articles are context, not new breaking news.</p></div><div><h3>Quiet hours and exclusions</h3><p>Quiet hours will delay delivery, not collection. Topic exclusions and watchlist membership must be checked again before sending.</p></div></div><ConfigurationLinks /></section>
  </>;
}

export default function NewsWorkspace() {
  const [section, setSection] = useState<Section>("calendar");
  const [company, setCompany] = useState("all");
  const [category, setCategory] = useState<TopicCategory | "all">("all");
  const scope = company === "all" ? "all seven pilot companies" : `${company} · ${PILOT.find((item) => item.ticker === company)?.name}`;
  function clearFilters() { setCompany("all"); setCategory("all"); }

  return <main id="main-content" tabIndex={-1} className={styles.workspace}>
    <div className={styles.titleRow}><div><p className="eyebrow">EVENTS, BUSINESS CONTEXT & EVIDENCE</p><h1>News & calendar</h1><p className={styles.subtitle}>Understand what changed, who it may affect, and what evidence supports the explanation.</p></div><Link href="/help" className={styles.helpLink}>How to use this view ↗</Link></div>
    <aside className={styles.configurationNotice} aria-label="Monitoring configuration"><strong>MONITORING UNCONFIGURED</strong><p>No news or calendar source, monitoring worker or alert delivery is connected here. Browse the proposed coverage and setup requirements below.</p></aside>
    <div className={styles.toolbar}>
      <div className={styles.sectionSwitch} role="group" aria-label="News workspace sections">{SECTIONS.map((item) => <button key={item.id} aria-pressed={section === item.id} aria-controls="news-section-panel" onClick={() => setSection(item.id)}>{item.label}</button>)}</div>
      <label className={styles.filter}><span>Watchlist scope</span><select value={company} onChange={(event) => setCompany(event.target.value)}><option value="all">All watchlist stocks · pilot</option>{PILOT.map((item) => <option key={item.ticker} value={item.ticker}>{item.ticker} · {item.name}</option>)}</select></label>
      {company !== "all" || category !== "all" ? <button className={styles.clearButton} onClick={clearFilters}>Clear filters</button> : null}
    </div>
    <p className={styles.selectionNote}>Pilot selection: CRCL, MSTR, COIN, HOOD, USAR, MP, GOOGL. View filters do not add stocks or start monitoring.</p>
    <div id="news-section-panel" className={styles.sectionContent}>
      {section === "calendar" ? <CalendarView scope={scope} /> : section === "topics" ? <TopicsView selectedCompany={company} category={category} setCategory={setCategory} clearFilters={clearFilters} /> : <HealthView />}
    </div>
    <footer className={styles.footer}>Development workspace · proposed coverage, no live news or verified event dates</footer>
  </main>;
}
