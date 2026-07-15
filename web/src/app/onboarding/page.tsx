"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LENS_ORDER, lensMeta } from "@/lib/lenses";
import { loadProfile, saveProfile } from "@/lib/profile";

const DETAIL: Record<string, string> = {
  general:
    "World news clustered into single stories with both sides, consequences, and a grounded agent to ask. The full picture, fast.",
  cyber_grc:
    "CVEs with CVSS, exploitation status, affected products, and control mapping — plus the cyber read of world events: who's exposed and what to check.",
  finance_trader:
    "Tickers, catalysts, and evidence-based price reads on market-moving news — plus the market read of everything else that happens in the world.",
};

export default function OnboardingPage() {
  const router = useRouter();
  const [selected, setSelected] = useState<string>("general");

  useEffect(() => {
    const existing = loadProfile();
    if (existing?.lens) setSelected(existing.lens);
  }, []);

  function submit() {
    saveProfile({ lens: selected });
    router.push("/feed");
  }

  return (
    <div className="mx-auto max-w-xl py-8">
      <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        How do you read the world?
      </h1>
      <p className="mt-2.5 text-sm leading-relaxed" style={{ color: "var(--ink-muted)" }}>
        Your lens sets the default: how your feed is ranked, which read of each story leads, and
        what the agent suggests asking. Every other lens stays one tap away on every story —
        switch anytime.
      </p>

      <div className="stagger mt-8 space-y-3">
        {LENS_ORDER.map((slug) => {
          const m = lensMeta(slug);
          const isSelected = selected === slug;
          return (
            <button
              key={slug}
              onClick={() => setSelected(slug)}
              className="card-hover block w-full rounded-2xl border p-5 text-left transition"
              style={{
                borderColor: isSelected ? m.color : "var(--line)",
                background: isSelected ? m.bg : "var(--bg-elevated)",
                boxShadow: isSelected ? `inset 0 0 0 1px ${m.color}` : undefined,
              }}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold" style={isSelected ? { color: m.color } : undefined}>
                  {m.name}
                </span>
                {isSelected && (
                  <span aria-hidden style={{ color: m.color }}>
                    ●
                  </span>
                )}
              </div>
              <p className="mt-1.5 text-sm leading-relaxed" style={{ color: "var(--ink-muted)" }}>
                {DETAIL[slug]}
              </p>
            </button>
          );
        })}
      </div>

      <button
        onClick={submit}
        className="mt-8 w-full rounded-full px-7 py-3.5 text-sm font-semibold transition hover:opacity-85"
        style={{ background: "var(--ink)", color: "var(--bg)" }}
      >
        Build my feed →
      </button>
      <p className="mt-3 text-center text-xs" style={{ color: "var(--ink-faint)" }}>
        No account needed — your lens lives in this browser.
      </p>
    </div>
  );
}
