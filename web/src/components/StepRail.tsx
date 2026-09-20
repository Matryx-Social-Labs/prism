"use client";

import { useEffect, useState } from "react";

/** The walkthrough's steps as a sticky rail on desktop; the one in view is marked. */
export function StepRail({ steps }: { steps: { id: string; n: string; label: string }[] }) {
  const [active, setActive] = useState(steps[0]?.id ?? "");
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const els = steps.map((s) => document.getElementById(s.id)).filter((e): e is HTMLElement => Boolean(e));
    const io = new IntersectionObserver(
      (entries) => {
        const vis = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (vis[0]) setActive(vis[0].target.id);
      },
      { rootMargin: "-30% 0px -55% 0px", threshold: 0 },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [steps]);
  return (
    <nav aria-label="Steps" className="hidden lg:block lg:sticky lg:top-[calc(var(--topbar)+24px)] lg:self-start">
      <ol className="flex flex-col gap-0.5">
        {steps.map((s) => (
          <li key={s.id}>
            <a href={`#${s.id}`} aria-current={active === s.id ? "step" : undefined} className={`flex items-center gap-3 rounded-[var(--r-md)] px-3 py-2 text-[14px] ${active === s.id ? "rail-on font-semibold" : ""}`} style={active === s.id ? undefined : { color: "var(--ink-2)" }}>
              <span className="font-mono text-[11px] tracking-[0.04em]" style={{ color: active === s.id ? "inherit" : "var(--ink-3)" }}>{s.n}</span>
              {s.label}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
