"use client";

export default function AnalysisReadinessError() {
  return <main id="main-content" className="setup-page" role="alert"><p className="eyebrow">ANALYSIS READINESS</p><h1>N/A</h1><p>The checked readiness snapshot could not be loaded.</p><button className="primary-link" onClick={() => window.location.reload()}>Retry</button></main>;
}
