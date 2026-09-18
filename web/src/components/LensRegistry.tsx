"use client";

import { useLenses } from "@/lib/lenses";

// The live registry, never a hand-typed list: the lens set grows on the
// backend and this renders whatever /api/v1/lenses returns (CLAUDE.md). Each
// row is a lens speaking, so its dot is the one place colour is allowed here.
export function LensRegistry() {
  const lenses = useLenses();
  return (
    <ul className="flex flex-col gap-2">
      {lenses.map((l) => (
        <li key={l.slug} className="card flex items-start gap-3 py-3">
          <span aria-hidden className="mt-[7px] inline-block h-2 w-2 shrink-0 rounded-full" style={{ background: l.color }} />
          <span className="min-w-0">
            <span className="text-[15px] font-semibold" style={{ color: "var(--ink)" }}>{l.name}</span>
            <span className="block text-[13.5px] leading-[1.5]" style={{ color: "var(--ink-2)" }}>{l.plain ?? l.tagline}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
