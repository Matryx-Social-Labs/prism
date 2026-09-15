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
import { fetchLanguages, type LanguageOption, setProfile, useSession } from "@/lib/session";
import { lensMeta } from "@/lib/lenses";

const STEPS = ["Where you are", "What you do", "What you follow"] as const;

// What each lens unlocks — shown on the "Your lens" preview card. Keyed by the
// three real lens slugs; professions never map to anything outside these.
const LENS_UNLOCKS: Record<string, string[]> = {
  reader: [
    "Every perspective, consequence & follow-up on a story",
    "Feed clustered into whole stories, not scattered headlines",
    'Agent asks: "What’s the full picture here?"',
  ],
  cyber: [
    "CVEs, CVSS & exploitation status on every story",
    "Feed weighted to incidents, exposure & control impact",
    'Agent asks: "Who’s exposed and what do I check?"',
  ],
  markets: [
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
  const [lens, setLens] = useState("reader");
  const [picks, setPicks] = useState<Picks>({});
  const [expanded, setExpanded] = useState<string | null>(null);
  const [groups, setGroups] = useState<ProfessionGroup[]>([]);
  const [profession, setProfession] = useState<ProfessionOption | null>(null);
  const session = useSession();
  const [name, setName] = useState("");
  const [languages, setLanguages] = useState<string[]>([]);
  const [langOptions, setLangOptions] = useState<LanguageOption[]>([]);
  const [consent, setConsent] = useState(false);
  const [saving, setSaving] = useState(false);

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
    fetchLanguages()
      .then((r) => {
        setLangOptions(r.languages);
        setLanguages((cur) => (cur.length ? cur : r.default));
      })
      .catch(() => {});
  }, []);

  function toggleLanguage(code: string) {
    setLanguages((cur) => (cur.includes(code) ? cur.filter((c) => c !== code) : [...cur, code]));
  }

  function pickProfession(p: ProfessionOption) {
    setProfession(p);
    setLens(p.lens);
    setPicks(interestsToPicks(p.interests));
  }

  async function finish() {
    // Client profile (lens/interests/state/languages) drives feed personalization locally.
    saveProfile({
      lens,
      region: "IN",
      state: state || null,
      interests: picksToInterests(picks),
      languages: languages.length ? languages : undefined,
    });
    // Account profile (name/profession/state/languages/consent) persists server-side
    // once the reader is signed in. Non-blocking: a failure never traps them here.
    if (session && name.trim() && profession && consent) {
      setSaving(true);
      try {
        await setProfile(session, {
          name: name.trim(),
          profession: profession.slug,
          state: state || null,
          languages,
          consent,
        });
      } catch {
        /* client profile is already saved; let them into the app */
      }
      setSaving(false);
    }
    router.push("/feed");
  }

  const meta = lensMeta(lens);
  const sectorName = (slug: string) =>
    taxonomy.find((s) => s.slug === slug)?.name ?? slug.charAt(0).toUpperCase() + slug.slice(1);

  return (
    <div className="mx-auto max-w-[720px] px-5 pb-20 pt-9 sm:px-8">
      {/* The three steps as codes on a rule, the current one underlined, the
          way the sector strip marks the active subject. Earlier steps are
          links back; later ones are not yet reachable. */}
      <nav
        className="hide-scroll mb-8 flex gap-4 overflow-x-auto border-b font-mono text-[10.5px] uppercase tracking-[0.06em]"
        style={{ borderColor: "var(--line)" }}
        aria-label={`Step ${step + 1} of 3`}
      >
        {STEPS.map((label, i) => (
          <button
            key={label}
            onClick={() => i < step && setStep(i)}
            disabled={i > step}
            aria-current={i === step ? "step" : undefined}
            className="flex h-11 shrink-0 items-end border-b-2 pb-2 pt-3 leading-none disabled:cursor-default"
            style={{
              borderColor: i === step ? "var(--ink)" : "transparent",
              color: i === step ? "var(--ink)" : "var(--ink-faint)",
            }}
          >
            {label}
          </button>
        ))}
      </nav>

      {step === 0 && (
        <section>
          <h1 className="text-[30px] font-medium leading-[1.15] text-balance sm:text-[34px]">
            Which state are you in?
          </h1>
          <p className="mt-3 max-w-[52ch] text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
            Prism leads with news from your state, then the rest of India. You can change it any time.
          </p>
          <label className="mt-7 block">
            <span className="mb-2 block text-[13.5px] font-medium">Your state</span>
            <StateSelect value={state} onChange={setState} />
          </label>

          {langOptions.length > 0 && (
            <div className="mt-9">
              <p className="text-[13.5px] font-medium">Languages you read</p>
              <div className="mt-3 flex flex-wrap gap-2.5">
                {langOptions.map((l) => {
                  const idx = languages.indexOf(l.code);
                  const sel = idx >= 0;
                  return (
                    <button
                      key={l.code}
                      type="button"
                      onClick={() => toggleLanguage(l.code)}
                      aria-pressed={sel}
                      aria-label={`${l.name}${sel ? `, preference ${idx + 1}` : ""}`}
                      className="flex min-h-[44px] items-center gap-2 rounded-full border px-4 text-[15px] transition"
                      style={{
                        borderColor: sel ? "var(--ink)" : "var(--line-strong)",
                        background: sel ? "var(--ink)" : "transparent",
                        color: sel ? "var(--bg)" : "var(--ink)",
                      }}
                    >
                      {l.native}
                      {sel && (
                        <span
                          className="text-[11px]"
                          style={{ fontFamily: "var(--font-mono), monospace", opacity: 0.7 }}
                        >
                          {idx + 1}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
              <p className="mt-3 text-[13px] leading-[1.5]" style={{ color: "var(--ink-muted)" }}>
                Your first pick leads. English stays as a fallback, so you never miss a story.
              </p>
            </div>
          )}
        </section>
      )}

      {step === 1 && (
        <section>
          <h1 className="text-[32px] font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            What do you do?
          </h1>
          <p className="mt-2.5 text-sm leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
            Your profession picks your lens: how stories are ranked, which fields are extracted,
            what the agent asks. Every other lens stays one tap away.
          </p>
          <label className="mt-6 flex flex-col gap-1.5">
            <span
              className="text-[10.5px] font-semibold uppercase tracking-[0.12em]"
              style={{ color: "var(--ink-faint)", fontFamily: "var(--font-mono), monospace" }}
            >
              Your name
            </span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Sagar"
              className="w-full max-w-[360px] rounded-[12px] border px-3.5 py-3 text-[16px] outline-none"
              style={{ borderColor: "var(--line-strong)", background: "var(--bg)", color: "var(--ink)" }}
            />
          </label>
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
                {(LENS_UNLOCKS[lens] ?? LENS_UNLOCKS.reader).map((line) => (
                  <span key={line}>◆ {line}</span>
                ))}
              </div>
              {profession && profession.interests.length > 0 && (
                <p className="mt-3 text-[11px]" style={{ color: "var(--ink-faint)" }}>
                  Interests pre-set to {profession.interests.map(sectorName).join(" + ")}. Refine them in the next step.
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
            Pre-set from your profession. Add or drop sectors, then narrow any of them to the
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

          {session && (
            <label className="mt-8 flex items-start gap-2.5 text-[13px] leading-[1.5]" style={{ color: "var(--ink-muted)" }}>
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-0.5 h-4 w-4 shrink-0"
              />
              <span>
                I agree to the Terms and to Prism creating an account for me and processing my
                email per the privacy policy.
              </span>
            </label>
          )}
        </section>
      )}

      <div className="mt-[34px] flex gap-3">
        {step > 0 && (
          <button
            onClick={() => setStep(step - 1)}
            className="rounded-full border px-6 py-[13px] text-sm font-semibold"
            style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
          >
            Back
          </button>
        )}
        <button
          onClick={() => (step < 2 ? setStep(step + 1) : finish())}
          disabled={saving || (step === 2 && !!session && (!name.trim() || !profession || !consent))}
          className="flex-1 rounded-full px-7 py-[13px] text-sm font-semibold transition hover:opacity-85 disabled:opacity-45"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          {saving ? "Saving…" : step < 2 ? "Continue" : "Build my feed"}
        </button>
      </div>
      <p className="mt-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-[12.5px]" style={{ color: "var(--ink-muted)" }}>
        <span>
          {session
            ? `Signed in as ${session.email}. This sets up your feed.`
            : "No account needed. Your profile lives in this browser."}
        </span>
        {/* Nothing blocks reading: the way out is on every step. */}
        <button onClick={() => router.push("/feed")} className="underline underline-offset-4" style={{ color: "var(--ink)" }}>
          Skip for now
        </button>
      </p>
    </div>
  );
}
