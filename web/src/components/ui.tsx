"use client";

import Link from "next/link";
import { useId } from "react";
import { ArrowLeft, Check } from "@/components/icons";

/**
 * The Design System v2 primitives the pages share (components/ui/*.jsx and
 * chrome/BackBar, chrome/StepIndicator in the Claude Design project), on the
 * system's own .p-* classes. Colour only through tokens; every state is a word.
 */

/** A dashed box whose title names what is missing, an optional line on why, and at most one action. */
export function EmptyState({ title, children, action }: { title: React.ReactNode; children?: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="grid gap-2 px-5 py-8" style={{ border: "1px dashed var(--line-strong)", borderRadius: "var(--r-lg)" }}>
      <p style={{ font: "var(--t-title-s)", color: "var(--ink)" }}>{title}</p>
      {children && <p className="max-w-[52ch]" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{children}</p>}
      {action && <div className="mt-1.5">{action}</div>}
    </div>
  );
}

/** What happened, in words, and one way on. Errors are announced (role=alert); info is a status. */
export function Alert({ tone = "info", title, children, action }: { tone?: "info" | "error"; title?: React.ReactNode; children?: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className={`p-alert p-alert--${tone}`} role={tone === "error" ? "alert" : "status"}>
      <div className="min-w-0 flex-1">
        {title && <p className="p-alert__title">{title}</p>}
        {children && <div style={{ color: "var(--ink-2)" }}>{children}</div>}
      </div>
      {action}
    </div>
  );
}

/** A short confirmation on ink ("Saved · your record is re-sorted"). The caller positions and times it. */
export function Toast({ children, icon = <Check size={16} /> }: { children: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <div className="p-toast" role="status">
      {icon}
      {children}
    </div>
  );
}

type TextFieldProps = {
  label: React.ReactNode;
  hint?: React.ReactNode;
  error?: React.ReactNode;
  value: string;
  onChange: (value: string) => void;
  multiline?: boolean;
  rows?: number;
  /** Something inside the field's right edge: a key hint, a clear button. */
  trailing?: React.ReactNode;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange">;

/** A labelled input (16px, so iOS never zooms). The error replaces the hint and marks the field invalid. */
export function TextField({ label, hint, error, value, onChange, multiline, rows = 4, trailing, id, maxLength, ...rest }: TextFieldProps) {
  const auto = useId();
  const fid = id ?? auto;
  const described = hint || error ? `${fid}-d` : undefined;
  const common = {
    id: fid,
    className: "p-input",
    value,
    maxLength,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": described,
  } as const;
  return (
    <div className="p-field">
      <label className="p-field__label" htmlFor={fid}>{label}</label>
      <div className="relative">
        {multiline ? (
          <textarea {...common} rows={rows} placeholder={rest.placeholder} name={rest.name} required={rest.required} disabled={rest.disabled} onChange={(e) => onChange(e.target.value)} />
        ) : (
          <input {...rest} {...common} onChange={(e) => onChange(e.target.value)} style={trailing ? { paddingRight: 48 } : undefined} />
        )}
        {trailing && <div className="absolute inset-y-0.5 right-1.5 flex items-center">{trailing}</div>}
      </div>
      {maxLength && multiline && <p className="p-count text-right">{value.length} / {maxLength}</p>}
      {error ? <p id={described} className="p-field__error">{error}</p> : hint ? <p id={described} className="p-field__hint">{hint}</p> : null}
    </div>
  );
}

export type SelectOption = string | { value: string; label: string };

/** A labelled native select, in the input's shape, with optional option groups. */
export function SelectField({ label, hint, value, onChange, options = [], groups, id, disabled, name, placeholder }: {
  label: React.ReactNode;
  hint?: React.ReactNode;
  /** The first, empty option ("Choose a state"); `value` "" selects it. */
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  options?: readonly SelectOption[];
  groups?: readonly { label: string; options: readonly SelectOption[] }[];
  id?: string;
  disabled?: boolean;
  name?: string;
}) {
  const auto = useId();
  const fid = id ?? auto;
  const opt = (o: SelectOption) => (typeof o === "string" ? <option key={o} value={o}>{o}</option> : <option key={o.value} value={o.value}>{o.label}</option>);
  return (
    <div className="p-field">
      <label className="p-field__label" htmlFor={fid}>{label}</label>
      <select id={fid} name={name} className="p-input" value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)} aria-describedby={hint ? `${fid}-d` : undefined}>
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {groups ? groups.map((g) => <optgroup key={g.label} label={g.label}>{g.options.map(opt)}</optgroup>) : options.map(opt)}
      </select>
      {hint && <p id={`${fid}-d`} className="p-field__hint">{hint}</p>}
    </div>
  );
}

/** A checkbox row, 44px tall; `native` prints a language's own name beside its English one. */
export function Checkbox({ checked, onChange, children, hint, native, disabled, name, value }: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  children: React.ReactNode;
  hint?: React.ReactNode;
  native?: string | null;
  disabled?: boolean;
  name?: string;
  value?: string;
}) {
  return (
    <label className="p-check">
      <input type="checkbox" checked={checked} disabled={disabled} name={name} value={value} onChange={(e) => onChange(e.target.checked)} />
      <span className="grid gap-0.5">
        <span>
          {children}
          {native && <span className="ml-2" style={{ color: "var(--ink-3)" }}>{native}</span>}
        </span>
        {hint && <span style={{ font: "var(--t-body-s)", fontSize: 13.5, color: "var(--ink-3)" }}>{hint}</span>}
      </span>
    </label>
  );
}

/** A setting that opens its own choices when on: the row is the switch, the chips sit under it. */
export function ToggleRow({ label, sub, on, onChange, children }: { label: string; sub?: React.ReactNode; on: boolean; onChange: (on: boolean) => void; children?: React.ReactNode }) {
  const choices = useId();
  return (
    <div className="border-t" style={{ borderColor: "var(--line)" }}>
      <button
        type="button"
        role="switch"
        aria-checked={on}
        // Turning it on opens its own choices: say so, and point at them.
        aria-expanded={children ? on : undefined}
        aria-controls={children && on ? choices : undefined}
        onClick={() => onChange(!on)}
        className="flex min-h-14 w-full items-center gap-3 py-2 text-left"
      >
        <span className="grid min-w-0 flex-1 gap-0.5">
          <span style={{ font: "600 15px/1.3 var(--font-read)", color: "var(--ink)" }}>{label}</span>
          {sub && <span style={{ font: "400 13.5px/1.4 var(--font-read)", color: "var(--ink-3)" }}>{sub}</span>}
        </span>
        <span className="p-switch" aria-checked={on} aria-hidden="true" />
      </button>
      {on && children && <div id={choices} className="flex flex-wrap gap-2 pb-3.5">{children}</div>}
    </div>
  );
}

/** Where a flow is: done steps in ink and revisitable, the current one in the accent, later ones faint and closed. */
export function StepIndicator({ steps, current, onPick }: { steps: readonly string[]; current: number; onPick?: (i: number) => void }) {
  return (
    <ol aria-label={`Step ${current + 1} of ${steps.length}`} className="grid gap-2" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }}>
      {steps.map((s, i) => {
        const state = i < current ? "done" : i === current ? "now" : "next";
        return (
          <li key={s} className="min-w-0">
            <button
              type="button"
              disabled={i > current}
              onClick={() => onPick?.(i)}
              aria-current={state === "now" ? "step" : undefined}
              className="grid min-h-11 w-full gap-1.5 text-left"
              style={{ color: state === "next" ? "var(--ink-3)" : "var(--ink)" }}
            >
              <span className="h-[3px] rounded-sm" style={{ background: state === "next" ? "var(--line)" : state === "now" ? "var(--accent)" : "var(--ink)" }} />
              <span style={{ font: `${state === "now" ? 600 : 500} 13px/1.2 var(--font-read)` }}>
                <span className="p-mono mr-1.5" style={{ fontSize: 11 }}>{i + 1}</span>
                {s}
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

/** The phone's way back: a sticky 52px bar with the place it returns to, and room for one action. */
export function BackBar({ label, href, onBack, right }: { label: string; href?: string; onBack?: () => void; right?: React.ReactNode }) {
  const inner = (
    <>
      <ArrowLeft size={18} />
      {label}
    </>
  );
  const cls = "inline-flex min-h-11 items-center gap-1.5 px-2";
  const style = { font: "600 15px/1 var(--font-read)", color: "var(--ink)" } as const;
  return (
    <header className="glass sticky top-0 z-30 flex h-[var(--masthead)] items-center gap-2 border-b px-2" style={{ borderColor: "var(--line)" }}>
      {href ? <Link href={href} className={cls} style={style}>{inner}</Link> : <button type="button" onClick={onBack} className={cls} style={style}>{inner}</button>}
      <span className="flex-1" />
      {right}
    </header>
  );
}

/** A long page's sections, numbered, with the one in view marked by an ink edge. */
export function OnThisPage({ items, current }: { items: readonly { id: string; label: string }[]; current?: string }) {
  return (
    <nav aria-label="On this page" className="grid gap-0.5">
      <p className="p-eyebrow mb-1.5">On this page</p>
      {items.map((it, i) => {
        const on = it.id === current;
        return (
          <a
            key={it.id}
            href={`#${it.id}`}
            aria-current={on ? "true" : undefined}
            className="grid grid-cols-[24px_1fr] px-2.5 py-[7px]"
            style={{ borderLeft: `2px solid ${on ? "var(--ink)" : "var(--line)"}`, font: `${on ? 600 : 500} 14px/1.3 var(--font-read)`, color: on ? "var(--ink)" : "var(--ink-2)" }}
          >
            <span className="p-mono" aria-hidden="true" style={{ fontSize: 11, color: "var(--ink-3)" }}>{String(i + 1).padStart(2, "0")}</span>
            {it.label}
          </a>
        );
      })}
    </nav>
  );
}

/** The page's point in one or two sentences, under a 3px ink rule. */
export function InShortCard({ children, title = "In short" }: { children: React.ReactNode; title?: string }) {
  return (
    <aside className="p-4" style={{ background: "var(--sunken)", borderTop: "var(--rule-section) solid var(--ink)" }}>
      <p className="p-eyebrow">{title}</p>
      <div className="mt-1.5" style={{ font: "var(--t-body-s)" }}>{children}</div>
    </aside>
  );
}

/** A small card of labelled facts. A row with an empty label prints the value alone (a link list). */
export function InfoCard({ title, rows }: { title: string; rows: readonly (readonly [string, React.ReactNode])[] }) {
  return (
    <aside className="p-card grid gap-2">
      <p className="p-eyebrow">{title}</p>
      <dl className="m-0 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5" style={{ font: "var(--t-body-s)" }}>
        {rows.map(([k, v], i) => (
          <div key={i} className="contents">
            {k && <dt style={{ color: "var(--ink-3)" }}>{k}</dt>}
            <dd className={`m-0 min-w-0 ${k ? "" : "col-span-2"}`} style={{ overflowWrap: "anywhere" }}>{v}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}

const SYSTEM = {
  404: { code: "404", title: "Not in the record", body: "There is no page at this address. It may have moved, or the link may be wrong." },
  error: { code: "500", title: "Something broke on our side", body: "Prism couldn't build this page. Nothing you did caused it. Try again in a minute." },
} as const;

/** The 404 and error pages (ui/SystemPage.jsx). The offline variant is not built: Prism has no offline mode. */
export function SystemPage({ kind, reference, onRetry }: { kind: keyof typeof SYSTEM; reference?: string; onRetry?: () => void }) {
  const c = SYSTEM[kind];
  return (
    <div className="mx-auto grid w-full max-w-[560px] gap-3.5 px-[var(--gutter)] py-12 lg:py-24">
      <p className="p-mono" style={{ fontSize: 12, color: "var(--ink-3)" }}>{c.code}{reference ? ` · ${reference}` : ""}</p>
      <h1 className="text-balance" style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>{c.title}</h1>
      <p style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>{c.body}</p>
      <div className="flex flex-wrap gap-2">
        {kind === "error" && onRetry ? (
          <>
            <button type="button" className="p-btn p-btn--primary" onClick={onRetry}>Try again</button>
            <Link href="/feed" className="p-btn p-btn--secondary">Today&rsquo;s record</Link>
          </>
        ) : (
          <Link href="/feed" className="p-btn p-btn--primary">Today&rsquo;s record</Link>
        )}
      </div>
    </div>
  );
}
