"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { interestsToPicks, picksToInterests, useTaxonomy, type Picks } from "@/components/ProfileEditor";
import { Field, ProfessionField, SectorsField, StateField, useProfessionGroups } from "@/components/ReservationForm";
import { loadProfile, saveProfile } from "@/lib/profile";
import type { ProfessionOption } from "@/lib/api";
import { setProfile, useSession } from "@/lib/session";

const STEPS = ["Where you are", "What you do", "What you follow"] as const;

export default function OnboardingPage() {
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
    router.push("/feed");
  }

  return (
    <div className="mx-auto max-w-[720px] px-5 pb-20 pt-9 sm:px-8">
      {/* The three steps as codes on a rule, the current one underlined, the
          way the sector strip marks the active subject. Earlier steps are
          links back; later ones are not yet reachable. */}
      <nav
        className="mb-8 flex flex-wrap gap-x-4 border-b font-mono text-[11px] uppercase tracking-[0.06em]"
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
            <span className="mr-1.5" style={{ color: i === step ? "var(--ink)" : "var(--ink-faint)" }}>{i + 1}</span>
            <span className={i === step ? "" : "sr-only sm:not-sr-only"}>{label}</span>
          </button>
        ))}
      </nav>

      {step === 0 && (
        <section>
          <h1 className="text-[30px] font-medium leading-[1.15] text-balance sm:text-[34px]">Which state are you in?</h1>
          <p className="mt-3 max-w-[52ch] text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
            You can change any of this later, under You.
          </p>
          <div className="mt-4">
            <StateField value={state} onChange={setState} />
          </div>
        </section>
      )}

      {step === 1 && (
        <section>
          <h1 className="text-[30px] font-medium leading-[1.15] text-balance sm:text-[34px]">What do you do?</h1>
          <div className="mt-4">
            {session && (
              <Field label="Your name" hint="For the account you are signed in to.">
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" aria-label="Your name" autoComplete="name"
                  className="h-12 w-full max-w-[360px] border px-4 text-[16px] outline-none"
                  style={{ borderColor: "var(--line-strong)", background: "var(--bg-elevated)", color: "var(--ink)" }} />
              </Field>
            )}
            <ProfessionField groups={groups} profession={profession?.slug ?? null} lens={lens} onPick={pickProfession} />
            {profession && profession.interests.length > 0 && (
              <p className="text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
                Subjects pre-set from your profession. Refine them in the next step.
              </p>
            )}
          </div>
        </section>
      )}

      {step === 2 && (
        <section>
          <h1 className="text-[30px] font-medium leading-[1.15] text-balance sm:text-[34px]">What do you follow?</h1>
          <div className="mt-4">
            <SectorsField taxonomy={taxonomy} picks={picks} onPicks={setPicks} />
          </div>
          {session && (
            <label className="mt-6 flex items-start gap-2.5 text-[13px] leading-[1.5]" style={{ color: "var(--ink-muted)" }}>
              <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 h-4 w-4 shrink-0" />
              <span>I agree to the Terms and to Prism creating an account for me and processing my email per the privacy policy.</span>
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
