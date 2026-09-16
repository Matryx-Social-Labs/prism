"use client";

import { useLenses } from "@/lib/lenses";

// The live registry, never a hand-typed list: the lens set grows on the
// backend and this renders whatever /api/v1/lenses returns (CLAUDE.md). Each
// row is a lens speaking, so its dot is the one place colour is allowed here.
export function LensRegistry() {
  const lenses = useLenses();
  return (
    <ul className="rule-live">
      {lenses.map((l) => (
        <li key={l.slug} className="flex items-baseline gap-3 border-b py-3" style={{ borderColor: "var(--line)" }}>
          <span aria-hidden className="inline-block h-[7px] w-[7px] shrink-0 translate-y-[-1px] rounded-full" style={{ background: l.color }} />
          <span className="min-w-0">
            <span className="text-[15.5px] font-medium" style={{ color: "var(--ink)" }}>{l.name}</span>
            <span className="block text-[13.5px] leading-[1.5]" style={{ color: "var(--ink-muted)" }}>{l.plain ?? l.tagline}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
