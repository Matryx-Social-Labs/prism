"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  InterestChips,
  StateSelect,
  interestsToPicks,
  picksToInterests,
  useTaxonomy,
  type Picks,
} from "@/components/ProfileEditor";
import { loadProfile, saveProfile } from "@/lib/profile";
import { fetchProfessions, type ProfessionGroup, type ProfessionOption } from "@/lib/api";
import { lensMeta } from "@/lib/lenses";

const STEPS = ["Where you are", "What you do", "What you follow"] as const;

// What each lens unlocks — shown on the "Your lens" preview card. Keyed by the
// three real lens slugs; professions never map to anything outside these.
const LENS_UNLOCKS: Record<string, string[]> = {
  general: [
    "Every perspective, consequence & follow-up on a story",
    "Feed clustered into whole stories, not scattered headlines",
    'Agent asks: "What’s the full picture here?"',
  ],
  cyber_grc: [
    "CVEs, CVSS & exploitation status on every story",
    "Feed weighted to incidents, exposure & control impact",
    'Agent asks: "Who’s exposed and what do I check?"',
  ],
  finance_trader: [
    "Tickers, catalysts & price reads on every story",
    "Feed weighted to market-moving news",
    'Agent asks: "Which tickers does this move?"',
  ],
};

export default function OnboardingPage() {
  const router = useRouter();
  const taxonomy = useTaxonomy();
  const [step, setStep] = useState(0);
  const [state, setState] = useState("");
  const [lens, setLens] = useState("general");
  const [picks, setPicks] = useState<Picks>({});
  const [expanded, setExpanded] = useState<string | null>(null);
  const [groups, setGroups] = useState<ProfessionGroup[]>([]);
  const [profession, setProfession] = useState<ProfessionOption | null>(null);

  useEffect(() => {
    const existing = loadProfile();
    if (existing) {
      setLens(existing.lens);
      if (existing.state) setState(existing.state);
      setPicks(interestsToPicks(existing.interests));
    }
  }, []);

  useEffect(() => {
    fetchProfessions().then(setGroups).catch(() => setGroups([]));
  }, []);

  function pickProfession(p: ProfessionOption) {
    setProfession(p);
    setLens(p.lens);
    setPicks(interestsToPicks(p.interests));
  }

  function finish() {
    saveProfile({ lens, region: "IN", state: state || null, interests: picksToInterests(picks) });
    router.push("/feed");
  }

  const meta = lensMeta(lens);
  const sectorName = (slug: string) =>
    taxonomy.find((s) => s.slug === slug)?.name ?? slug.charAt(0).toUpperCase() + slug.slice(1);

  return (
    <div className="mx-auto max-w-[720px] px-5 pb-20 pt-9 sm:px-8">
      <div className="mb-[30px] flex items-center justify-between">
        <div className="flex items-center gap-2.5" aria-label={`Step ${step + 1} of 3`}>
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
                  color: i < step ? "var(--bg)" : "inherit",
                }}
              >
                {i + 1}
              </span>
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>
        <button
          onClick={() => router.push("/feed")}
          className="text-[12.5px] underline underline-offset-[3px]"
          style={{ color: "var(--ink-faint)" }}
        >
          Skip for now
        </button>
      </div>

      {step === 0 && (
        <section>
          <h1 className="text-[32px] font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            Which state are you in?
          </h1>
          <p className="mt-2.5 text-sm leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
            Prism leads with news from your state, then the rest of India. Pick your state —
            you can change it anytime.
          </p>
          <div className="mt-6">
            <StateSelect value={state} onChange={setState} />
          </div>
        </section>
      )}

      {step === 1 && (
        <section>
          <h1 className="text-[32px] font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            What do you do?
          </h1>
          <p className="mt-2.5 text-sm leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
            Your profession picks your lens — how stories are ranked, which fields are extracted,
            what the agent asks. Every other lens stays one tap away.
          </p>
          <div className="mt-6 grid grid-cols-1 items-start gap-6 lg:grid-cols-[1fr_320px]">
            {/* Grouped profession list */}
            <div
              className="overflow-hidden rounded-[14px] border"
              style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
            >
              <div
                className="flex items-center justify-between border-b px-4 py-3 text-sm"
                style={{ borderColor: "var(--line)" }}
              >
                <span className="font-medium" style={{ color: profession ? "var(--ink)" : "var(--ink-faint)" }}>
                  {profession ? profession.label : "Choose your profession"}
                </span>
                <span aria-hidden style={{ color: "var(--ink-faint)" }}>
                  ▾
                </span>
              </div>
              <div className="max-h-[320px] overflow-auto py-2">
                {groups.map((g) => (
                  <div key={g.group}>
                    <p
                      className="px-4 pb-1 pt-1.5 text-[10.5px] font-semibold uppercase tracking-[0.1em]"
                      style={{ color: "var(--ink-faint)" }}
                    >
                      {g.group}
                    </p>
                    {g.options.map((o) => {
                      const sel = profession?.slug === o.slug;
                      return (
                        <button
                          key={o.slug}
                          onClick={() => pickProfession(o)}
                          className="block w-full px-4 py-2 text-left text-[13.5px]"
                          style={{
                            fontWeight: sel ? 600 : 400,
                            background: sel ? "var(--bg-sunken)" : "transparent",
                            color: sel ? "var(--ink)" : "var(--ink-muted)",
                          }}
                        >
                          {o.label}
                          {sel && " ✓"}
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>

            {/* "Your lens" preview — the one place color is allowed */}
            <div
              className="rounded-[18px] border-[1.5px] px-5 py-[18px]"
              style={{ borderColor: meta.color, background: meta.bg }}
            >
              <span
                className="text-[10.5px] font-semibold uppercase tracking-[0.14em]"
                style={{ color: meta.color }}
              >
                Your lens
              </span>
              <p className="mt-2 text-base font-semibold" style={{ color: "var(--ink)" }}>
                {meta.short}
              </p>
              <div className="mt-3 flex flex-col gap-[7px] text-[12.5px] leading-[1.5]" style={{ color: "var(--ink-muted)" }}>
                {(LENS_UNLOCKS[lens] ?? LENS_UNLOCKS.general).map((line) => (
                  <span key={line}>◆ {line}</span>
                ))}
              </div>
              {profession && profession.interests.length > 0 && (
                <p className="mt-3 text-[11px]" style={{ color: "var(--ink-faint)" }}>
                  Interests pre-set to {profession.interests.map(sectorName).join(" + ")} — refine in the next step.
                </p>
              )}
            </div>
          </div>
        </section>
      )}

      {step === 2 && (
        <section>
          <h1 className="text-[32px] font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            What do you follow?
          </h1>
          <p className="mt-2.5 text-sm leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
            Pre-set from your profession — add or drop sectors, then narrow any of them to the
            sub-domains you actually care about (cricket, AI, elections…). Pick nothing and you get
            everything.
          </p>
          <div className="mt-6">
            <InterestChips
              taxonomy={taxonomy}
              picks={picks}
              expanded={expanded}
              onPicks={setPicks}
              onExpanded={setExpanded}
            />
          </div>
        </section>
      )}

      <div className="mt-[34px] flex gap-3">
        {step > 0 && (
          <button
            onClick={() => setStep(step - 1)}
            className="rounded-full border px-6 py-[13px] text-sm font-semibold"
            style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
          >
            ← Back
          </button>
        )}
        <button
          onClick={() => (step < 2 ? setStep(step + 1) : finish())}
          className="flex-1 rounded-full px-7 py-[13px] text-sm font-semibold transition hover:opacity-85"
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
