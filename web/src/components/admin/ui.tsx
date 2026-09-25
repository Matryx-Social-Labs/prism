"use client";

/**
 * The small parts every admin list shares: a search box, a filter switch that
 * says how many each choice holds, a state badge, and a k-of-n bar. The bar
 * prints its count beside it — the length is a picture of the number, never
 * the only place it is.
 */

import { SearchIcon } from "@/components/icons";

export function SearchBox({ value, onChange, label }: { value: string; onChange: (v: string) => void; label: string }) {
  return (
    <label className="relative block w-full max-w-[320px]">
      <span className="sr-only">{label}</span>
      <span aria-hidden className="pointer-events-none absolute inset-y-0 left-3 flex items-center" style={{ color: "var(--ink-3)" }}>
        <SearchIcon size={16} />
      </span>
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={label}
        className="p-input"
        style={{ minHeight: 44, paddingLeft: 36, fontSize: 15 }}
      />
    </label>
  );
}

/** A choice of filters, each with its count: "Open 3". */
export function FilterSeg<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: ReadonlyArray<{ value: T; label: string; count: number }>;
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="p-seg p-hide-scroll max-w-full overflow-x-auto" role="tablist" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" role="tab" aria-selected={value === o.value} onClick={() => onChange(o.value)}>
          {o.label}
          <span className="p-chip__count tabular-nums">{o.count}</span>
        </button>
      ))}
    </div>
  );
}

/** A state in words on a hairline (p-badge--outline). `strong` for the state that asks for attention. */
export function Badge({ children, strong }: { children: React.ReactNode; strong?: boolean }) {
  return (
    <span className="p-badge p-badge--outline" style={strong ? { borderColor: "var(--ink)", color: "var(--ink)" } : undefined}>
      {children}
    </span>
  );
}

/** KofNBar: the words, "k of n" in mono, and a flat ink bar under them. */
export function Progress({ label, done, total }: { label: string; done: number; total: number }) {
  const pct = total > 0 ? Math.min(100, (done / total) * 100) : 0;
  return (
    <div className="grid gap-1">
      <p className="flex items-baseline justify-between gap-3 text-[12.5px] font-medium" style={{ color: "var(--ink-2)" }}>
        <span>{label}</span>
        <span className="font-mono text-[11.5px] tabular-nums" style={{ color: "var(--ink)" }}>
          {done.toLocaleString("en-IN")} of {total.toLocaleString("en-IN")}
        </span>
      </p>
      <div className="h-1.5" style={{ background: "var(--sunken)" }} aria-hidden>
        <div className="h-full" style={{ width: `${pct}%`, background: "var(--ink)" }} />
      </div>
    </div>
  );
}

/** Case-blind match of a query against any of the given fields. */
export const matches = (q: string, ...fields: Array<string | null | undefined>) => {
  const needle = q.trim().toLowerCase();
  return !needle || fields.some((f) => f?.toLowerCase().includes(needle));
};
