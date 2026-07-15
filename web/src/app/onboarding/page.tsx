"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchTaxonomy, type TaxonomySector } from "@/lib/api";
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

// Common regions first; "Other / everywhere" opts out of regional scoping.
const REGIONS: [string, string][] = [
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

const STEPS = ["Where you are", "How you read", "What you follow"] as const;

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [region, setRegion] = useState<string>("IN");
  const [lens, setLens] = useState<string>("general");
  const [taxonomy, setTaxonomy] = useState<TaxonomySector[]>([]);
  // sector slug → null (whole sector) | set of subsector slugs
  const [picks, setPicks] = useState<Record<string, Set<string> | null>>({});
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    const existing = loadProfile();
    if (existing) {
      setLens(existing.lens);
      if (existing.region) setRegion(existing.region);
      const restored: Record<string, Set<string> | null> = {};
      for (const token of existing.interests) {
        const [sec, sub] = token.split(":");
        if (sub) {
          const cur = restored[sec];
          restored[sec] = cur instanceof Set ? cur.add(sub) : new Set([sub]);
        } else if (!(sec in restored)) {
          restored[sec] = null;
        }
      }
      setPicks(restored);
    }
    fetchTaxonomy().then(setTaxonomy).catch(() => setTaxonomy([]));
  }, []);

  const interests = useMemo(() => {
    const out: string[] = [];
    for (const [sec, subs] of Object.entries(picks)) {
      if (subs === null || subs.size === 0) out.push(sec);
      else for (const sub of subs) out.push(`${sec}:${sub}`);
    }
    return out;
  }, [picks]);

  function toggleSector(slug: string) {
    setPicks((prev) => {
      const next = { ...prev };
      if (slug in next) {
        delete next[slug];
        if (expanded === slug) setExpanded(null);
      } else {
        next[slug] = null;
        setExpanded(slug);
      }
      return next;
    });
  }

  function toggleSub(sector: string, sub: string) {
    setPicks((prev) => {
      const cur = prev[sector];
      const subs = cur instanceof Set ? new Set(cur) : new Set<string>();
      if (subs.has(sub)) subs.delete(sub);
      else subs.add(sub);
      return { ...prev, [sector]: subs.size ? subs : null };
    });
  }

  function submit() {
    saveProfile({ lens, region, interests });
    router.push("/feed");
  }

  return (
    <div className="mx-auto max-w-xl py-8">
      <div className="mb-6 flex items-center gap-2" aria-label={`Step ${step + 1} of 3`}>
        {STEPS.map((label, i) => (
          <button
            key={label}
            onClick={() => i < step && setStep(i)}
            className="flex items-center gap-2 text-xs font-semibold"
            style={{ color: i === step ? "var(--ink)" : "var(--ink-faint)" }}
          >
            <span
              className="flex h-6 w-6 items-center justify-center rounded-full border text-[11px]"
              style={{
                borderColor: i <= step ? "var(--ink)" : "var(--line)",
                background: i < step ? "var(--ink)" : "transparent",
                color: i < step ? "var(--bg)" : undefined,
              }}
            >
              {i + 1}
            </span>
            <span className="hidden sm:inline">{label}</span>
            {i < STEPS.length - 1 && <span aria-hidden style={{ color: "var(--line)" }}>—</span>}
          </button>
        ))}
      </div>

      {step === 0 && (
        <section>
          <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            Where do you read from?
          </h1>
          <p className="mt-2.5 text-sm leading-relaxed" style={{ color: "var(--ink-muted)" }}>
            Your feed blends international coverage with news from your region, and flags stories
            your region&apos;s outlets haven&apos;t covered yet.
          </p>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="mt-6 w-full rounded-2xl border p-4 text-sm"
            style={{ borderColor: "var(--line)", background: "var(--bg-elevated)", color: "var(--ink)" }}
            aria-label="Your region"
          >
            {REGIONS.map(([code, name]) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </select>
        </section>
      )}

      {step === 1 && (
        <section>
          <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            How do you read the world?
          </h1>
          <p className="mt-2.5 text-sm leading-relaxed" style={{ color: "var(--ink-muted)" }}>
            Your lens sets the default read of each story. Every other applicable lens stays one
            tap away — switch anytime.
          </p>
          <div className="stagger mt-6 space-y-3">
            {LENS_ORDER.map((slug) => {
              const m = lensMeta(slug);
              const isSelected = lens === slug;
              return (
                <button
                  key={slug}
                  onClick={() => setLens(slug)}
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
        </section>
      )}

      {step === 2 && (
        <section>
          <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            What do you follow?
          </h1>
          <p className="mt-2.5 text-sm leading-relaxed" style={{ color: "var(--ink-muted)" }}>
            Pick sectors — then narrow any of them to the sub-domains you actually care about
            (cricket, AI, markets…). Pick nothing and you get everything.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            {taxonomy.map((sec) => {
              const selected = sec.slug in picks;
              return (
                <button
                  key={sec.slug}
                  onClick={() => (selected && expanded !== sec.slug ? setExpanded(sec.slug) : toggleSector(sec.slug))}
                  className="rounded-full border px-4 py-2 text-sm font-semibold transition"
                  style={{
                    borderColor: selected ? "var(--ink)" : "var(--line)",
                    background: selected ? "var(--ink)" : "var(--bg-elevated)",
                    color: selected ? "var(--bg)" : "var(--ink-muted)",
                  }}
                >
                  {sec.name}
                  {picks[sec.slug] instanceof Set && picks[sec.slug]!.size > 0 && (
                    <span className="ml-1.5 rounded-full px-1.5 text-xs" style={{ background: "var(--bg)", color: "var(--ink)" }}>
                      {picks[sec.slug]!.size}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          {expanded && (picks[expanded] !== undefined) && (
            <div className="mt-4 rounded-2xl border p-4" style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}>
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--ink-faint)" }}>
                {taxonomy.find((s) => s.slug === expanded)?.name} — narrow it down (optional)
              </p>
              <div className="flex flex-wrap gap-2">
                {taxonomy
                  .find((s) => s.slug === expanded)
                  ?.subsectors.map((sub) => {
                    const on = picks[expanded] instanceof Set && (picks[expanded] as Set<string>).has(sub.slug);
                    return (
                      <button
                        key={sub.slug}
                        onClick={() => toggleSub(expanded, sub.slug)}
                        className="rounded-full border px-3 py-1.5 text-xs font-semibold transition"
                        style={{
                          borderColor: on ? "var(--accent, var(--ink))" : "var(--line)",
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
        </section>
      )}

      <div className="mt-8 flex gap-3">
        {step > 0 && (
          <button
            onClick={() => setStep(step - 1)}
            className="rounded-full border px-6 py-3.5 text-sm font-semibold"
            style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
          >
            ← Back
          </button>
        )}
        <button
          onClick={() => (step < 2 ? setStep(step + 1) : submit())}
          className="flex-1 rounded-full px-7 py-3.5 text-sm font-semibold transition hover:opacity-85"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          {step < 2 ? "Continue →" : "Build my feed →"}
        </button>
      </div>
      <p className="mt-3 text-center text-xs" style={{ color: "var(--ink-faint)" }}>
        No account needed — your profile lives in this browser.
      </p>
    </div>
  );
}
