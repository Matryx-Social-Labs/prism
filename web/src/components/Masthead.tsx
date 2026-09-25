import { Brand } from "@/components/Brand";
import { ThemeToggle } from "@/components/ThemeToggle";

/**
 * The phone masthead: the brand, the dateline in mono, the theme toggle — 52px,
 * sticky, glass. Hidden from lg, where the top bar carries the brand. `right`
 * takes a control that belongs to the page (the scope switch on the chart).
 */
export function Masthead({ dateline, right }: { dateline: string | null; right?: React.ReactNode }) {
  return (
    <header className="glass sticky top-0 z-30 -mx-[var(--gutter)] grid h-[var(--masthead)] grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border-b pl-[var(--gutter)] pr-2 lg:hidden" style={{ borderColor: "var(--line)" }}>
      <Brand size={22} label="Prism, today" />
      <span className="min-w-0 truncate text-right font-mono text-[11px] uppercase" style={{ color: "var(--ink-3)" }}>
        {dateline}
      </span>
      <div className="flex shrink-0 items-center gap-1">
        {right}
        <ThemeToggle />
      </div>
    </header>
  );
}
