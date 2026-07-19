"use client";

// Shared building blocks for onboarding and the interests editor:
// region grid, lens cards/pills, sector chips with sub-domain narrowing.
// Picks shape: { [sector]: null (whole sector) | string[] (subsectors) }.

import { useEffect, useState } from "react";
import { fetchTaxonomy, type TaxonomySector } from "@/lib/api";
import { useLenses } from "@/lib/lenses";

export type Picks = Record<string, string[] | null>;

export const REGIONS: [string, string][] = [
  ["IN", "India"],
  ["US", "United States"],
  ["GB", "United Kingdom"],
  ["AE", "United Arab Emirates"],
  ["SG", "Singapore"],
  ["AU", "Australia"],
  ["CA", "Canada"],
  ["DE", "Germany"],
  ["FR", "France"],
  ["JP", "Japan"],
  ["BR", "Brazil"],
  ["ZA", "South Africa"],
];

export const LENS_DETAIL: Record<string, string> = {
  general:
    "World news clustered into single stories with every perspective, consequences, and a grounded agent to ask. The full picture, fast.",
  cyber_grc:
    "CVEs with CVSS, exploitation status, affected products, and control mapping — plus the cyber read of world events: who's exposed and what to check.",
  finance_trader:
    "Tickers, catalysts, and evidence-based price reads on market-moving news — plus the market read of everything else that happens in the world.",
};

export function picksToInterests(picks: Picks): string[] {
  const out: string[] = [];
  for (const [sec, subs] of Object.entries(picks)) {
    if (!subs || subs.length === 0) out.push(sec);
    else for (const sub of subs) out.push(`${sec}:${sub}`);
  }
  return out;
}

export function interestsToPicks(interests: string[]): Picks {
  const picks: Picks = {};
  for (const token of interests) {
    const [sec, sub] = token.split(":");
    if (sub) {
      const cur = picks[sec];
      picks[sec] = Array.isArray(cur) ? [...cur, sub] : [sub];
    } else if (!(sec in picks)) {
      picks[sec] = null;
    }
  }
  return picks;
}

export function useTaxonomy(): TaxonomySector[] {
  const [taxonomy, setTaxonomy] = useState<TaxonomySector[]>([]);
  useEffect(() => {
    fetchTaxonomy().then(setTaxonomy).catch(() => setTaxonomy([]));
  }, []);
  return taxonomy;
}

export function RegionGrid({ value, onChange }: { value: string; onChange: (code: string) => void }) {
  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
      {REGIONS.map(([code, name]) => {
        const sel = value === code;
        return (
          <button
            key={code}
            onClick={() => onChange(code)}
            className="rounded-[14px] border px-4 py-3 text-left text-[13.5px] font-semibold transition"
            style={{
              borderColor: sel ? "var(--ink)" : "var(--line)",
              background: sel ? "var(--ink)" : "var(--bg-elevated)",
              color: sel ? "var(--bg)" : "var(--ink-muted)",
            }}
          >
            {name}
          </button>
        );
      })}
    </div>
  );
}

export function LensCards({ value, onChange }: { value: string; onChange: (slug: string) => void }) {
  const lenses = useLenses();
  return (
    <div className="stagger flex flex-col gap-3">
      {lenses.map((m) => {
        const slug = m.slug;
        const sel = value === slug;
        return (
          <button
            key={slug}
            onClick={() => onChange(slug)}
            className="card-hover rounded-[18px] border px-5 py-[18px] text-left transition"
            style={{
              borderColor: sel ? m.color : "var(--line)",
              boxShadow: sel ? `inset 0 0 0 1px ${m.color}` : undefined,
              background: sel ? m.bg : "var(--bg-elevated)",
            }}
          >
            <span className="flex items-center justify-between">
              <span className="text-[15px] font-semibold" style={{ color: sel ? m.color : "var(--ink)" }}>
                {m.name}
              </span>
              {sel && (
                <span aria-hidden style={{ color: m.color }}>
                  ●
                </span>
              )}
            </span>
            <span className="mt-1.5 block text-[13.5px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
              {LENS_DETAIL[slug] ?? m.tagline}
            </span>
          </button>
        );
      })}
      <div className="rounded-[18px] border-[1.5px] border-dashed px-5 py-4" style={{ borderColor: "var(--line-strong)" }}>
        <span className="text-[13px] font-semibold" style={{ color: "var(--ink-faint)" }}>
          More lenses on the way
        </span>
        <span className="mt-1 block text-[12.5px]" style={{ color: "var(--ink-faint)" }}>
          New roles are added continuously as lenses on the same backbone.
        </span>
      </div>
    </div>
  );
}

export function LensPills({ value, onChange }: { value: string; onChange: (slug: string) => void }) {
  const lenses = useLenses();
  return (
    <div className="flex flex-wrap gap-2">
      {lenses.map((m) => {
        const slug = m.slug;
        const sel = value === slug;
        return (
          <button
            key={slug}
            onClick={() => onChange(slug)}
            className="rounded-full border px-4 py-2 text-[13px] font-semibold transition"
            style={{
              borderColor: sel ? m.color : "var(--line)",
              background: sel ? m.bg : "var(--bg-elevated)",
              color: sel ? m.color : "var(--ink-muted)",
            }}
          >
            {m.name}
          </button>
        );
      })}
      <span
        className="rounded-full border-[1.5px] border-dashed px-4 py-2 text-[13px] font-semibold"
        style={{ borderColor: "var(--line-strong)", color: "var(--ink-faint)" }}
      >
        More soon
      </span>
    </div>
  );
}

export function InterestChips({
  taxonomy,
  picks,
  expanded,
  onPicks,
  onExpanded,
}: {
  taxonomy: TaxonomySector[];
  picks: Picks;
  expanded: string | null;
  onPicks: (picks: Picks) => void;
  onExpanded: (slug: string | null) => void;
}) {
  const expSec = taxonomy.find((s) => s.slug === expanded);
  return (
    <>
      <div className="flex flex-wrap gap-2">
        {taxonomy.map((sec) => {
          const sel = sec.slug in picks;
          const nsubs = Array.isArray(picks[sec.slug]) ? (picks[sec.slug] as string[]).length : 0;
          return (
            <button
              key={sec.slug}
              onClick={() => {
                const next = { ...picks };
                if (sec.slug in next) {
                  if (expanded !== sec.slug) {
                    onExpanded(sec.slug);
                    return;
                  }
                  delete next[sec.slug];
                  onPicks(next);
                  onExpanded(null);
                } else {
                  next[sec.slug] = null;
                  onPicks(next);
                  onExpanded(sec.slug);
                }
              }}
              className="rounded-full border px-4 py-2 text-[13px] font-semibold transition"
              style={{
                borderColor: sel ? "var(--ink)" : "var(--line)",
                background: sel ? "var(--ink)" : "var(--bg-elevated)",
                color: sel ? "var(--bg)" : "var(--ink-muted)",
              }}
            >
              {sec.name}
              {nsubs > 0 && ` · ${nsubs}`}
            </button>
          );
        })}
      </div>
      {expSec && expanded && expanded in picks && expSec.subsectors.length > 0 && (
        <div className="mt-4 rounded-2xl border p-4" style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}>
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest" style={{ color: "var(--ink-faint)" }}>
            {expSec.name} — narrow it down (optional)
          </p>
          <div className="flex flex-wrap gap-2">
            {expSec.subsectors.map((sub) => {
              const cur = picks[expSec.slug];
              const on = Array.isArray(cur) && cur.includes(sub.slug);
              return (
                <button
                  key={sub.slug}
                  onClick={() => {
                    const next = { ...picks };
                    let arr = Array.isArray(next[expSec.slug]) ? [...(next[expSec.slug] as string[])] : [];
                    if (arr.includes(sub.slug)) arr = arr.filter((x) => x !== sub.slug);
                    else arr.push(sub.slug);
                    next[expSec.slug] = arr.length ? arr : null;
                    onPicks(next);
                  }}
                  className="rounded-full border px-[13px] py-1.5 text-xs font-semibold transition"
                  style={{
                    borderColor: on ? "var(--ink)" : "var(--line)",
                    background: on ? "var(--bg-sunken)" : "transparent",
                    color: on ? "var(--ink)" : "var(--ink-muted)",
                  }}
                >
                  {sub.name}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}
