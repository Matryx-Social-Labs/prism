import { Brand } from "@/components/Brand";
import { ThemeToggle } from "@/components/ThemeToggle";

/**
 * The phone masthead: the brand, the dateline in mono, the theme toggle — 52px,
 * sticky, glass. Hidden from lg, where the top bar carries the brand. `right`
 * takes a control that belongs to the page (the scope switch on the chart).
 * The dateline steps down by the masthead's content width (the viewport less
 * its 24px of padding) instead of clipping (screens/Wordmark.html): ≥420
 * `dateline` · 340–419 `datelineM` · <340 `datelineS`, each falling back to the
 * next longer one; globals.css picks.
 */
export function Masthead({ dateline, datelineM, datelineS, right }: {
  dateline: string | null;
  datelineM?: string | null;
  datelineS?: string | null;
  right?: React.ReactNode;
}) {
  const m = datelineM ?? dateline;
  return (
    <header className="p-masthead glass sticky top-0 z-30 -mx-[var(--gutter)] grid h-[var(--masthead)] grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border-b pl-[var(--gutter)] pr-2 lg:hidden" style={{ borderColor: "var(--line)" }}>
      <Brand size={20} />
      <span className="min-w-0 truncate text-right font-mono text-[11px] uppercase" style={{ color: "var(--ink-3)" }}>
        <span className="p-dateline__l">{dateline}</span>
        <span className="p-dateline__m">{m}</span>
        <span className="p-dateline__s">{datelineS ?? m}</span>
      </span>
      <div className="flex shrink-0 items-center gap-1">
        {right}
        <ThemeToggle />
      </div>
    </header>
  );
}
