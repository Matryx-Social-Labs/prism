"use client";

import { useMemo, useState } from "react";
import type { BranchTreeData, StoryDevelopment } from "@/lib/api";
import { routeShape } from "@/lib/route";
import { shortDate } from "@/lib/dateline";

/**
 * The attention curve under the route map: sources per day across every
 * line of the story, to scale. Off by default; a toggle shows it, because it
 * answers a second question (how loud, when) the map does not ask.
 */
export function Attention({ tree, developments }: { tree: BranchTreeData; developments: StoryDevelopment[] }) {
  const [on, setOn] = useState(false);
  const shape = useMemo(() => routeShape(tree, developments), [tree, developments]);
  const all = [...shape.trunk, ...shape.lines.flatMap((l) => l.stations), ...shape.satellites];
  const perDay = Array.from({ length: shape.days }, (_, d) => all.filter((s) => s.day === d).reduce((n, s) => n + (s.source_count ?? 1), 0));
  const max = Math.max(1, ...perDay);
  const W = 1000, H = 70, x0 = 20, xd = (d: number) => x0 + d * ((W - 40) / Math.max(1, shape.days - 1));
  const d = perDay.map((v, i) => `${i ? "L" : "M"}${xd(i)} ${H - 18 - (v / max) * 44}`).join(" ") + ` L${xd(shape.days - 1)} ${H - 18} L${xd(0)} ${H - 18} Z`;
  const day0 = shape.day0 ? shortDate(shape.day0) : "";
  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setOn((v) => !v)}
        aria-pressed={on}
        className="flex h-11 items-center border-b-2 font-mono text-[11px]"
        style={{ borderColor: on ? "var(--ink)" : "transparent", color: on ? "var(--ink)" : "var(--ink-muted)" }}
      >
        Attention · sources per day
      </button>
      {on && (
        <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 block w-full" role="img" aria-label="Sources per day, all lines">
          <path d={d} style={{ fill: "var(--bg-sunken)" }} />
          {Array.from({ length: shape.days }, (_, i) => i).filter((i) => i % 2 === 0).map((i) => (
            <text key={i} x={xd(i)} y={H - 2} textAnchor="middle" className="rm-lab">{i === 0 ? day0 : `+${i}d`}</text>
          ))}
        </svg>
      )}
    </div>
  );
}
