"use client";

// The scope bottom sheet, shared by Feed and Trending.
//
// It was copy-pasted between the two and drifted: Trending kept a stale copy of
// the disabled rule and never got the "why is this greyed out" title, and the
// two option lists disagreed about what the widest tier was called. One of those
// drifts shipped. The disabled predicate genuinely differs per surface — the
// Feed's National tier is state-relative, Trending's is absolute — so that stays
// a prop rather than being flattened into a shared rule.

type Props<T extends string> = {
  open: boolean;
  onClose: () => void;
  /** [value, label] in display order. */
  options: readonly (readonly [T, string])[];
  selected: T;
  onSelect: (value: T) => void;
  /** Why a row can't be chosen, or null when it can. Doubles as the title text. */
  disabledReason?: (value: T) => string | null;
  /** Extra classes for the positioning wrapper (the Feed scopes it to its column). */
  className?: string;
};

export function ScopeSheet<T extends string>({
  open,
  onClose,
  options,
  selected,
  onSelect,
  disabledReason,
  className = "",
}: Props<T>) {
  if (!open) return null;

  return (
    <div className={`fixed inset-0 z-50 flex flex-col justify-end ${className}`}>
      <button
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0"
        style={{ background: "var(--scrim)" }}
      />
      <div
        className="relative rounded-t-[22px] px-5 pb-11 pt-3"
        style={{ background: "var(--bg-elevated)", boxShadow: "var(--shadow-pop)" }}
      >
        <div className="mx-auto mb-3.5 h-1 w-9 rounded-full" style={{ background: "var(--line-strong)" }} />
        <h3 className="text-[18px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
          Scope
        </h3>
        <p className="mb-3 mt-1 text-[12.5px]" style={{ color: "var(--ink-muted)" }}>
          Applies everywhere — Feed, Trending, Pulse and Search.
        </p>
        {options.map(([value, label]) => {
          // A greyed row with no reason reads as a broken control, and disabled
          // buttons leave the tab order, so a screen reader gets nothing at all.
          const reason = disabledReason?.(value) ?? null;
          return (
            <button
              key={value}
              onClick={() => {
                onSelect(value);
                onClose();
              }}
              disabled={reason !== null}
              title={reason ?? undefined}
              className="flex min-h-[48px] w-full items-center gap-2.5 border-b px-1 text-left text-[14.5px] disabled:opacity-40"
              style={{
                borderColor: "var(--line)",
                color: "var(--ink)",
                fontWeight: selected === value ? 600 : 500,
              }}
            >
              <span>{label}</span>
              {selected === value && <span className="ml-auto">✓</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}
