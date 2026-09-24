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
export const FREE_LINE =
  "The evidence is free and stays free: every record, every report behind it, every verified quote, the coverage and its count, and the story status, for every reader, with or without an account. What can be paid for is depth and convenience: more questions, professional readings, watchlists and alerts.";

export function StatusColumn({ tone, label, items }: { tone: "now" | "val" | "next"; label: string; items: string[] }) {
  const color = tone === "now" ? "var(--lens-markets)" : tone === "val" ? "var(--status-disputed)" : "var(--ink-3)";
  return (
    <div className="card">
      <h3 className="mb-3 text-[12.5px] font-semibold uppercase tracking-[0.08em]" style={{ color }}>{label}</h3>
      <ul className="flex flex-col gap-2 text-[14.5px] leading-[1.5]" style={{ color: "var(--ink-2)" }}>
        {items.map((item) => (
          <li key={item} className="flex gap-2.5">
            <span aria-hidden className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: color, opacity: 0.6 }} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
