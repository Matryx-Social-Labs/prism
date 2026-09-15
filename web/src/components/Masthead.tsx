import Link from "next/link";
import { PrismMark } from "@/components/PrismMark";
import { ThemeToggle } from "@/components/ThemeToggle";

/**
 * The chart's masthead: the mark and name, then the dateline in the provenance
 * voice as a second line — date · sources · stories — the way the chart at the
 * platform carries its train, date and coach count above the list.
 *
 * No kicker, no eyebrow (craft floor: a heading carries its own weight).
 * The mark is the existing logo, unchanged.
 *
 * On desktop the brand header (SiteHeader) already carries the mark and the
 * theme toggle, so here they are phone-only — two stacked wordmarks was the
 * original double-header bug. The dateline stays at every width.
 */
export function Masthead({ dateline, right }: { dateline: string | null; right?: React.ReactNode }) {
  return (
    <header className="flex items-end justify-between gap-4 pb-3 pt-4">
      <div className="min-w-0">
        <Link href="/" className="flex items-center gap-2 lg:hidden" aria-label="Prism, today's chart">
          <PrismMark />
          <span
            className="text-[26px] leading-none"
            style={{ fontFamily: "var(--font-display), sans-serif", letterSpacing: "0.01em" }}
          >
            PRISM
          </span>
        </Link>
        {dateline && (
          <p className="mt-1.5 truncate font-mono text-[11px] tracking-[0.04em]" style={{ color: "var(--ink-muted)" }}>
            {dateline}
          </p>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-3">
        {right}
        <span className="lg:hidden">
          <ThemeToggle />
        </span>
      </div>
    </header>
  );
}
