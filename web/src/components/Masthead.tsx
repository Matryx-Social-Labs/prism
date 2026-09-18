import { Brand } from "@/components/Brand";
import { ThemeToggle } from "@/components/ThemeToggle";

/**
 * The phone masthead: the brand, the dateline in mono, the theme toggle — 52px,
 * sticky, glass. Hidden from lg, where the top bar carries the brand. `right`
 * takes a control that belongs to the page (the scope switch on the chart).
 */
export function Masthead({ dateline, right }: { dateline: string | null; right?: React.ReactNode }) {
  return (
    <header className="glass sticky top-0 z-30 -mx-5 flex h-[52px] items-center justify-between gap-3 border-b px-5 sm:-mx-8 sm:px-8 lg:hidden" style={{ borderColor: "var(--line)" }}>
      <Brand size={24} label="Prism, today" />
      {dateline && (
        <span className="min-w-0 truncate font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--ink-3)" }}>
          {dateline}
        </span>
      )}
      <div className="flex shrink-0 items-center gap-1">
        {right}
        <ThemeToggle />
      </div>
    </header>
  );
}
