import Link from "next/link";
import { Reveal } from "@/components/Reveal";

/** Where Prism stands: what is live, what is being validated, what is next. Shared by the landing and the walkthrough. */
export const AVAILABLE = [
  "One record per story from monitored outlets, across languages",
  "Every count out of the public list of monitored outlets, with when they were last read",
  "Single-source stories marked as not yet corroborated",
  "Verbatim quotes with the source and the article context",
  "Coverage by outlet origin on every story",
  "Professional readings of the same facts",
  "Ask, cited to the story's own reports",
  "A public corrections log, and every earlier version of a record",
];
export const VALIDATION = [
  "Story timelines across days (two-reviewer gate)",
  "Freshness targets on a clean 72-hour cohort",
  "Coverage gaps stated against the monitored set",
];
// Translation of Prism's own writing is held until the record and its data
// quality are complete (founder D-d, 2026-09-24), so it is not promised here.
export const NEXT = [
  "Each line of a brief linked to the report it came from",
  "More Indian-language outlets, the most-read languages first",
  "Follow a story and see only what changed since you last read",
];

/** The truth layer is never the premium feature (strategy report, 2026-09-24). */
export const FREE_EVIDENCE =
  "The evidence is free and stays free: every record, every report behind it, every verified quote, the coverage and its count, and the story status, for every reader, with or without an account.";
export const FREE_LINE = `${FREE_EVIDENCE} What can be paid for is depth and convenience: more questions, professional readings, watchlists and alerts.`;
/** What Plus carries today, as the pricing page lists it (components/PlusPage.tsx). */
const PLUS_LINE = "More questions a day, answers drawn from the whole story, and a larger model on every answer.";

// State is line form (Design System v2): solid is live, dashed is being
// validated, dotted is not built yet. The label says it too; the rule never
// carries the meaning alone.
const RULE = { now: "solid", val: "dashed", next: "dotted" } as const;

export function StatusColumn({ tone, label, items }: { tone: keyof typeof RULE; label: string; items: string[] }) {
  return (
    <div className="pt-3" style={{ borderTop: `3px ${RULE[tone]} var(--ink)` }}>
      <h3 className="p-eyebrow">{label}</h3>
      <ul className="mt-2 grid gap-1.5">
        {items.map((item) => <li key={item} style={{ font: "var(--t-body-s)" }}>{item}</li>)}
      </ul>
    </div>
  );
}

/** Available now · In validation · Next, each printing in as it is reached. */
export function StatusColumns() {
  const cols = [["now", "Available now", AVAILABLE], ["val", "In validation", VALIDATION], ["next", "Next", NEXT]] as const;
  return (
    <div className="mt-[18px] grid gap-5 lg:grid-cols-3">
      {cols.map(([tone, label, items], i) => (
        <Reveal key={tone} delay={i * 90}><StatusColumn tone={tone} label={label} items={[...items]} /></Reveal>
      ))}
    </div>
  );
}

/** Free and Plus, side by side. The price is the pricing source's own (`plusFrom`), or not printed. */
export function PlanCards({ plusFrom }: { plusFrom: string | null }) {
  return (
    <div className="mt-7 grid gap-3 lg:grid-cols-2">
      <div className="p-card">
        <h3 className="p-eyebrow">Free</h3>
        <p className="mt-1.5" style={{ font: "var(--t-body-s)" }}>{FREE_EVIDENCE}</p>
      </div>
      <div className="p-card" style={{ borderTop: "3px solid var(--accent)" }}>
        <h3 className="p-eyebrow" style={{ color: "var(--accent)" }}>Prism Plus{plusFrom ? ` · from ${plusFrom} a month` : ""}</h3>
        <p className="mt-1.5" style={{ font: "var(--t-body-s)" }}>{PLUS_LINE} <Link href="/plus" className="p-link">See Plus</Link></p>
      </div>
    </div>
  );
}
