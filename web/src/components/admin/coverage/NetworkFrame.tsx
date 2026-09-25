"use client";

/**
 * The 3D coverage network's frame (Design System v2 · admin/NetworkFrame): its
 * title, then one of four states — closed (a button; nothing loads until a
 * founder asks), loading, open (the graph, its key, who is left out), or a
 * sentence where the browser has no WebGL. The tables above always carry the
 * same numbers.
 */

import { SeriesKey } from "@/components/admin/charts/ChartPanel";

export type NetState = "closed" | "open" | "nowebgl";

/** Whether this browser can draw WebGL at all (switched off counts as no). */
export function hasWebGL(): boolean {
  const probe = document.createElement("canvas");
  return !!(probe.getContext("webgl2") ?? probe.getContext("webgl"));
}

/** The dashed ground a closed, loading or undrawable network sits on. */
export function NetStage({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="grid min-h-[260px] place-items-center rounded-[var(--r-md)] p-4 text-center"
      style={{ border: "1px dashed var(--line-strong)", background: "var(--sunken)" }}
    >
      {children}
    </div>
  );
}

export function NetworkFrame({
  state,
  onOpen,
  legend = [],
  left = 0,
  children,
}: {
  state: NetState;
  onOpen: () => void;
  legend?: Array<{ label: string; color: string; total?: string }>;
  /** Outlets that shared no story, so have no place in the network. */
  left?: number;
  children?: React.ReactNode;
}) {
  return (
    <section className="admin-panel grid gap-2.5" aria-label="Which outlets share stories">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="min-w-0 flex-1 text-[15px] font-semibold leading-[1.3]">Which outlets share stories</h2>
        {state === "open" && (
          <span className="text-[12.5px]" style={{ color: "var(--ink-3)" }}>
            Drag to turn, scroll to zoom, hover for a name.
          </span>
        )}
      </div>
      {state === "closed" && (
        <NetStage>
          <button type="button" className="p-btn p-btn--secondary" onClick={onOpen}>
            Open the 3D network
          </button>
        </NetStage>
      )}
      {state === "nowebgl" && (
        <NetStage>
          <p className="max-w-[44ch]" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
            This browser can&apos;t draw the 3D network. The tables above hold the same links.
          </p>
        </NetStage>
      )}
      {state === "open" && (
        <>
          {children}
          <div className="flex flex-wrap items-center gap-x-3.5 gap-y-1">
            <div className="min-w-0 flex-1 [&>ul]:mt-0">
              <SeriesKey items={legend} />
            </div>
            <span className="text-[12.5px]" style={{ color: "var(--ink-3)" }}>
              Sphere: stories. Line: stories shared, darker the more.
            </span>
          </div>
          {left > 0 && (
            <p className="text-[12.5px]" style={{ color: "var(--ink-2)" }}>
              {left} {left === 1 ? "outlet" : "outlets"} with no shared story {left === 1 ? "is" : "are"} left out; the outlets table lists{" "}
              {left === 1 ? "it" : "them"}.
            </p>
          )}
        </>
      )}
    </section>
  );
}
