"use client";

/**
 * The small parts every admin page shares (Design System v2 · admin/*): a
 * search field, the FilterSwitch (chips that say how many each choice holds),
 * a state badge, the KofNBar, a row action, an inline confirm and SwitchRow.
 * A bar prints its count beside it — the length is a picture of the number,
 * never the only place it is.
 */

import { TextField } from "@/components/ui";

/** The list's search: a labelled field, as wide as the row allows. */
export function SearchBox({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <div className="min-w-0 flex-[1_1_240px]">
      <TextField type="search" label="Search" placeholder={placeholder} value={value} onChange={onChange} />
    </div>
  );
}

/** FilterSwitch: one choice of several, each chip with its count ("Open 3"). */
export function FilterSwitch<T extends string>({
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
    <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className="p-chip"
          onClick={() => onChange(o.value)}
          style={{ minHeight: 34, padding: "0 12px", fontSize: 13 }}
        >
          {o.label}
          <span className="p-chip__count tabular-nums">{o.count.toLocaleString("en-IN")}</span>
        </button>
      ))}
    </div>
  );
}

/** A state in words. Ink for the settled state, outline for a fact, dashed for
 *  what is not (yet) so — the line carries it, never a hue. */
export function Badge({ children, tone = "outline" }: { children: React.ReactNode; tone?: "ink" | "outline" | "dashed" }) {
  return <span className={`p-badge p-badge--${tone}`}>{children}</span>;
}

/** KofNBar: the words, "k of n" in mono, and a flat ink bar under them. */
export function KofNBar({ label, k, n }: { label: string; k: number; n: number }) {
  const pct = n > 0 ? Math.min(100, (k / n) * 100) : 0;
  return (
    <div className="grid min-w-0 gap-1">
      <p className="flex items-baseline justify-between gap-3 text-[12.5px] font-medium leading-none" style={{ color: "var(--ink-2)" }}>
        <span>{label}</span>
        <span className="font-mono text-[11.5px] tabular-nums">
          {k.toLocaleString("en-IN")} of {n.toLocaleString("en-IN")}
        </span>
      </p>
      <div className="h-1.5" style={{ background: "var(--sunken)" }} aria-hidden>
        <div className="h-full" style={{ width: `${pct}%`, background: "var(--ink)" }} />
      </div>
    </div>
  );
}

/** A row action: a small button with a full 44px tap area. */
export function Act({
  onClick,
  variant = "ghost",
  disabled,
  children,
}: {
  onClick: () => void;
  variant?: "ghost" | "secondary" | "primary" | "destructive";
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} className={`p-btn p-btn--${variant} p-btn--sm p-hit`}>
      {children}
    </button>
  );
}

/** Asked in place, under what it acts on: what will happen, then yes or no. */
export function Confirm({
  children,
  yes,
  no = "Keep",
  danger,
  busy,
  onYes,
  onNo,
}: {
  children: React.ReactNode;
  yes: string;
  no?: string;
  danger?: boolean;
  busy?: boolean;
  onYes: () => void;
  onNo: () => void;
}) {
  return (
    <div
      role="group"
      aria-label={yes}
      className="flex flex-wrap items-center gap-2.5 rounded-[var(--r-md)] border p-3"
      style={{ borderColor: "var(--line-strong)", font: "var(--t-body-s)" }}
    >
      <span className="min-w-0 flex-[1_1_240px]">{children}</span>
      <Act variant={danger ? "destructive" : "primary"} onClick={onYes} disabled={busy}>
        {yes}
      </Act>
      <Act onClick={onNo}>{no}</Act>
    </div>
  );
}

/** SwitchRow: what the setting does, its name in mono, its state at the end —
 *  ON solid ink, OFF on a dashed edge, a word and nothing that looks flippable. */
export function SwitchRow({ name, does, on }: { name: string; does: string; on: boolean }) {
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-t py-3" style={{ borderColor: "var(--line)" }}>
      <span className="min-w-0">
        <span className="block text-[14.5px] font-medium leading-[1.35]" style={{ color: "var(--ink)" }}>{does}</span>
        <span className="block font-mono text-[11.5px] [overflow-wrap:anywhere]" style={{ color: "var(--ink-3)" }}>{name}</span>
      </span>
      <span className="p-tag-mono" style={on ? { background: "var(--ink)", color: "var(--paper)", borderColor: "var(--ink)" } : { borderStyle: "dashed" }}>
        {on ? "ON" : "OFF"}
      </span>
    </li>
  );
}

/** Case-blind match of a query against any of the given fields. */
export const matches = (q: string, ...fields: Array<string | null | undefined>) => {
  const needle = q.trim().toLowerCase();
  return !needle || fields.some((f) => f?.toLowerCase().includes(needle));
};
