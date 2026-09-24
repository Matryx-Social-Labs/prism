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
        className="h-[40px] w-full rounded-[var(--r-md)] border pl-9 pr-3 text-[15px]"
        style={{ borderColor: "var(--line-strong)", background: "var(--surface)" }}
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
    <div className="seg max-w-full overflow-x-auto" role="tablist" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" role="tab" aria-selected={value === o.value} onClick={() => onChange(o.value)}>
          {o.label}
          <span className="font-mono text-[11px] tabular-nums" style={{ color: "var(--ink-3)" }}>{o.count}</span>
        </button>
      ))}
    </div>
  );
}

/** A state in words on a hairline. `strong` for the state that asks for attention. */
export function Badge({ children, strong }: { children: React.ReactNode; strong?: boolean }) {
  return (
    <span
      className="inline-flex items-center rounded-[var(--r-sm)] border px-1.5 py-px text-[12px] font-semibold leading-5"
      style={{ borderColor: strong ? "var(--ink)" : "var(--line-strong)", color: strong ? "var(--ink)" : "var(--ink-2)" }}
    >
      {children}
    </span>
  );
}

export function Progress({ label, done, total }: { label: string; done: number; total: number }) {
  const pct = total > 0 ? Math.min(100, (done / total) * 100) : 0;
  return (
    <div>
      <p className="flex items-baseline justify-between gap-3 text-[13px]" style={{ color: "var(--ink-2)" }}>
        <span>{label}</span>
        <span className="font-mono text-[12px] tabular-nums" style={{ color: "var(--ink)" }}>
          {done.toLocaleString("en-IN")} of {total.toLocaleString("en-IN")}
        </span>
      </p>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full" style={{ background: "var(--sunken)" }} aria-hidden>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: "var(--viz-1)" }} />
      </div>
    </div>
  );
}

/** Case-blind match of a query against any of the given fields. */
export const matches = (q: string, ...fields: Array<string | null | undefined>) => {
  const needle = q.trim().toLowerCase();
  return !needle || fields.some((f) => f?.toLowerCase().includes(needle));
};
