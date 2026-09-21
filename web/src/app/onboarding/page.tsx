"use client";

import Link from "next/link";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { safeNext } from "@/lib/next";
import { interestsToPicks, picksToInterests, useTaxonomy, type Picks } from "@/components/ProfileEditor";
import { Field, ProfessionField, SectorsField, StateField, useProfessionGroups } from "@/components/ReservationForm";
import { loadProfile, saveProfile } from "@/lib/profile";
import type { ProfessionOption } from "@/lib/api";
import { setProfile, useSession } from "@/lib/session";

const STEPS = ["Where you are", "What you do", "What you follow"] as const;

function OnboardingPage() {
  const router = useRouter();
  const taxonomy = useTaxonomy();
  const groups = useProfessionGroups();
  const [step, setStep] = useState(0);
  const [state, setState] = useState("");
  const [lens, setLens] = useState("reader");
  const [picks, setPicks] = useState<Picks>({});
  const [profession, setProfession] = useState<ProfessionOption | null>(null);
  const session = useSession();
  const [name, setName] = useState("");
  const [consent, setConsent] = useState(false);
  // Where the reader was going before sign-in interrupted (a gate, /plus).
  const next = safeNext(useSearchParams().get("next")) ?? "/feed";
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const existing = loadProfile();
    if (existing) {
      setLens(existing.lens);
      if (existing.state) setState(existing.state);
      setPicks(interestsToPicks(existing.interests));
    }
  }, []);

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
      // English only for now (founder, 2026-09-16); languages are not collected.
      languages: loadProfile()?.languages ?? ["en"],
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
          languages: ["en"],
          consent,
        });
      } catch {
        /* client profile is already saved; let them into the app */
      }
      setSaving(false);
    }
    router.push(next);
  }

  return (
    <div className="mx-auto max-w-[var(--reading)] px-5 pb-20 pt-8 sm:px-8 lg:max-w-[760px]">
      {/* Three steps as a stepper: the current one filled, earlier ones are links
          back, later ones not yet reachable. Nothing blocks reading. */}
      <nav className="mb-7 flex items-center gap-2" aria-label={`Step ${step + 1} of 3`}>
        {STEPS.map((label, i) => (
          <button
            key={label}
            onClick={() => i < step && setStep(i)}
            disabled={i > step}
            aria-current={i === step ? "step" : undefined}
            className="flex min-h-11 items-center gap-2 disabled:cursor-default"
          >
            <span
              className="inline-flex h-7 w-7 items-center justify-center rounded-full text-[12.5px] font-semibold"
              style={i === step ? { background: "var(--accent)", color: "var(--on-accent)" } : i < step ? { background: "var(--accent-soft)", color: "var(--accent)" } : { background: "var(--sunken)", color: "var(--ink-3)" }}
            >
              {i + 1}
            </span>
            <span className={`text-[13.5px] font-medium ${i === step ? "" : "sr-only sm:not-sr-only"}`} style={{ color: i === step ? "var(--ink)" : "var(--ink-3)" }}>{label}</span>
            {i < STEPS.length - 1 && <span aria-hidden className="ml-1 hidden h-px w-6 sm:inline-block" style={{ background: "var(--line-strong)" }} />}
          </button>
        ))}
      </nav>

      <div className="border-y py-6 sm:border sm:p-8" style={{ borderColor: "var(--line-strong)", background: "var(--surface)" }}>
        {step === 0 && (
          <section>
            <h1 className="font-record text-[30px] font-bold leading-[1.25] text-balance sm:text-[34px]">Which state are you in?</h1>
            <p className="mt-2 max-w-[52ch] text-[15px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>You can change any of this later, under You.</p>
            <div className="mt-4">
              <StateField value={state} onChange={setState} />
            </div>
          </section>
        )}

        {step === 1 && (
          <section>
            <h1 className="font-record text-[30px] font-bold leading-[1.25] text-balance sm:text-[34px]">What do you do?</h1>
            <div className="mt-4">
              {session && (
                <Field label="Your name" hint="For the account you are signed in to.">
                  <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" aria-label="Your name" autoComplete="name" className="input max-w-[360px]" />
                </Field>
              )}
              <ProfessionField groups={groups} profession={profession?.slug ?? null} lens={lens} onPick={pickProfession} />
              {profession && profession.interests.length > 0 && (
                <p className="text-[13.5px]" style={{ color: "var(--ink-2)" }}>Subjects pre-set from your profession. Refine them in the next step.</p>
              )}
            </div>
          </section>
        )}

        {step === 2 && (
          <section>
            <h1 className="font-record text-[30px] font-bold leading-[1.25] text-balance sm:text-[34px]">What do you follow?</h1>
            <div className="mt-4">
              <SectorsField taxonomy={taxonomy} picks={picks} onPicks={setPicks} />
            </div>
            {session && (
              <label className="mt-5 flex items-start gap-2.5 text-[13.5px] leading-[1.5]" style={{ color: "var(--ink-2)" }}>
                <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--accent)]" />
                <span>
                  I agree to the <Link href="/terms" className="underline underline-offset-[3px]">Terms</Link> and to Prism creating an account for me and processing my email per the{" "}
                  <Link href="/privacy" className="underline underline-offset-[3px]">privacy policy</Link>.
                </span>
              </label>
            )}
          </section>
        )}

        <div className="mt-6 flex gap-2 border-t pt-5" style={{ borderColor: "var(--line)" }}>
          {step > 0 && (
            <button onClick={() => setStep(step - 1)} className="btn btn-secondary btn-lg">Back</button>
          )}
          <button
            onClick={() => (step < 2 ? setStep(step + 1) : finish())}
            disabled={saving || (step === 2 && !!session && (!name.trim() || !profession || !consent))}
            className="btn btn-primary btn-lg flex-1"
          >
            {saving ? "Saving…" : step < 2 ? "Continue" : "Build my feed"}
          </button>
        </div>
      </div>
      <p className="mt-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-[13px]" style={{ color: "var(--ink-3)" }}>
        <span>
          {session
            ? `Signed in as ${session.email}. This sets up your feed.`
            : "No account needed. Your profile lives in this browser."}
        </span>
        {/* Nothing blocks reading: the way out is on every step. */}
        <button onClick={() => router.push(next)} className="font-semibold underline-offset-4 hover:underline" style={{ color: "var(--accent)" }}>
          Skip for now
        </button>
      </p>
    </div>
  );
}

// useSearchParams (the `next` destination) needs a Suspense boundary for static rendering.
export default function Page() {
  return (
    <Suspense fallback={null}>
      <OnboardingPage />
    </Suspense>
  );
}
