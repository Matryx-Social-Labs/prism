/** Where Prism stands: what is live, what is being validated, what is next. Shared by the landing and the walkthrough. */
export const AVAILABLE = [
  "One record per story from monitored outlets, across languages",
  "Verbatim quotes with the source and the article context",
  "Coverage by outlet origin on every story",
  "Reader, Markets and Cyber readings of the same facts",
  "Ask, cited to the story's own reports",
];
export const VALIDATION = [
  "Story timelines across days (two-reviewer gate)",
  "Freshness targets on a clean 72-hour cohort",
  "Coverage gaps stated against the monitored set",
];
export const NEXT = [
  "Follow a story and see only what changed since you last read",
  "Original-language quotes beside the translation",
  "A corrections log on every record",
];

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
