import Link from "next/link";
import { Reveal } from "@/components/Reveal";

/** Where Prism stands: what is live, what is being validated, what is next. Shared by the landing and the walkthrough. */
export const AVAILABLE = [
  "One page per story, from outlets in English and Indian languages",
  "Every count is out of a public list of outlets, with when each was last read",
  "A story only one outlet has is marked as not yet corroborated",
  "Quotes in their exact words, linked to the line in the article",
  "Which kinds of outlet have each story, and how many",
  "Lenses: the same story read for a kind of work",
  "Ask a story a question; the answer cites its reports",
  "A public corrections log, and every earlier version of a story page",
];
export const VALIDATION = [
  "Timelines of stories that run for days (two reviewers check each)",
  "How quickly new reports reach a story page",
  "Saying which monitored outlets have not covered a story",
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
// The watchlist is free and alerts are not built, so neither is sold here.
export const FREE_LINE = `${FREE_EVIDENCE} What can be paid for is depth and convenience: every lens on every story and more questions.`;
/** What Plus carries today, as the pricing page lists it (components/PlusPage.tsx). Never a model (PRODUCT.md). */
const PLUS_LINE = "Every lens on every story, more questions a day, and answers drawn from the whole story.";

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

/** Working now · Being checked · Next, each printing in as it is reached. */
export function StatusColumns() {
  const cols = [["now", "Working now", AVAILABLE], ["val", "Being checked", VALIDATION], ["next", "Next", NEXT]] as const;
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
        <p className="mt-1.5" style={{ font: "var(--t-body-s)" }}>{PLUS_LINE} <Link href="/plus?from=landing" data-cta="landing:plans" className="p-link">See Plus</Link></p>
      </div>
    </div>
  );
}
