"use client";

import { useState } from "react";
import styles from "./help.module.css";

export type GlossaryEntry = {
  id: string;
  term: string;
  category: string;
  definition: string;
  detail?: string;
};

export default function Glossary({ entries }: { entries: readonly GlossaryEntry[] }) {
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const matches = (entry: GlossaryEntry) =>
    `${entry.term} ${entry.category} ${entry.definition} ${entry.detail ?? ""}`
      .toLocaleLowerCase().includes(normalizedQuery);
  const visibleCount = entries.filter(matches).length;

  return <div className={styles.glossary}>
    <div className={styles.searchControls}>
      <label htmlFor="glossary-search">Find a term or concept</label>
      <div className={styles.searchRow}>
        <input id="glossary-search" type="search" value={query}
          placeholder="Try TTM, coverage, cash flow…"
          onChange={(event) => setQuery(event.target.value)}
          aria-describedby="glossary-count" aria-controls="glossary-entries" />
        {query ? <button type="button" onClick={() => setQuery("")}>Clear search</button> : null}
      </div>
      <p id="glossary-count" className={styles.searchCount} role="status">
        {visibleCount} of {entries.length} definitions shown. Examples are illustrative.
      </p>
    </div>
    {visibleCount === 0 ? <p className={styles.noResults}>No matching term. Try a shorter word, or clear your search to browse all definitions.</p> : null}
    <dl id="glossary-entries" className={styles.entries}>
      {entries.map((entry) => <div key={entry.id} id={entry.id}
        className={styles.entry} hidden={!matches(entry)}>
        <dt><span>{entry.term}</span><span className={styles.category}>{entry.category}</span></dt>
        <dd>{entry.definition}{entry.detail ? <p className={styles.termDetail}>{entry.detail}</p> : null}</dd>
      </div>)}
    </dl>
  </div>;
}
