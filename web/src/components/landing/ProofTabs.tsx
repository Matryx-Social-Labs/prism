"use client";

import { useState } from "react";
import { Reveal } from "@/components/Reveal";

/**
 * "The record, not a verdict." (Design System v2 · screens/LandingPage `Proof`):
 * three cards side by side on a desk, three tabs on a phone. The panels are
 * rendered by the server from one real story; this only chooses which one a
 * phone shows. CSS decides the layout, so server and client agree on first paint.
 */
export type ProofPanel = { key: string; title: string; desc: string; body: React.ReactNode };

export function ProofTabs({ panels }: { panels: ProofPanel[] }) {
  const [tab, setTab] = useState(0);
  return (
    <>
      <div className="sc-tabs mt-[18px] lg:hidden">
        {panels.map((p, i) => (
          <a
            key={p.key}
            href={`#proof-${p.key}`}
            aria-current={tab === i ? "true" : undefined}
            onClick={(e) => { e.preventDefault(); setTab(i); }}
            className="inline-flex min-h-[44px] items-center"
          >
            {p.title}
          </a>
        ))}
      </div>
      <div className="mt-4 grid gap-4 lg:mt-7 lg:grid-cols-3">
        {panels.map((p, i) => (
          <div key={p.key} id={`proof-${p.key}`} className={`min-w-0 ${tab === i ? "" : "hidden lg:block"}`}>
            <Reveal delay={i * 100} className="grid content-start gap-3">
              <div className="hidden lg:block">
                <h3 style={{ font: "var(--t-title)" }}>{p.title}</h3>
                <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>{p.desc}</p>
              </div>
              <div className="min-w-0">{p.body}</div>
            </Reveal>
          </div>
        ))}
      </div>
    </>
  );
}
