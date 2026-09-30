import type { ReactNode } from "react";
import { exact } from "./presentation";
import styles from "./valuation.module.css";

export type InspectEvidence = (title: string, evidence: unknown) => void;

/** Display a saved value with one keyboard-accessible path to its evidence. */
export default function EvidenceValue({ title, value, display, evidence = value, onInspect, className, onSelect, pressed }: {
  title: string;
  value: unknown;
  display?: ReactNode;
  evidence?: unknown;
  onInspect: InspectEvidence;
  className?: string;
  onSelect?: () => void;
  pressed?: boolean;
}) {
  const label = typeof display === "string" ? display : exact(value);
  return <button type="button" className={`${styles.evidenceValue} ${className ?? ""}`}
    data-evidence-value={title} aria-label={`${title}: ${label}. Inspect evidence`}
    aria-pressed={pressed} onClick={() => { onSelect?.(); onInspect(title, evidence); }}>
    {display ?? exact(value)}
  </button>;
}
