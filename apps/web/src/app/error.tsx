"use client";
export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="setup-page" role="alert"><div className="eyebrow">SECTOR EXPLORER</div><h1>The snapshot could not load.</h1><p>No financial values are shown without their source records. Retry the saved snapshot.</p><button className="primary-link" onClick={reset}>Retry</button></main>;
}
