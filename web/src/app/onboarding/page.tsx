"use client";

import Link from "next/link";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { safeNext } from "@/lib/next";
import { SubjectToggles, followedSubjects, groupOn, interestsToPicks, picksToInterests, useRegions, useTaxonomy, useProfessionGroups, type Picks } from "@/components/ProfileEditor";
import { OnboardingPreview } from "@/components/accounts/OnboardingPreview";
import { ArrowLeft, Check } from "@/components/icons";
import { Alert, Checkbox, SelectField, StepIndicator, TextField } from "@/components/ui";
import { loadProfile, saveProfile } from "@/lib/profile";
import type { ProfessionOption } from "@/lib/api";
import { lensMeta } from "@/lib/lenses";
import { SECTOR_GROUPS } from "@/lib/sectors";
import { setProfile, useSession } from "@/lib/session";

/**
 * Onboarding (Design System v2 · Accounts board, flow 03): three steps — where
 * you are, what you do, what you follow — with the step indicator (earlier steps
 * revisitable), Skip for now on every step, and nothing that blocks reading.
 * The board's fourth step (languages) is still PROPOSED and not built: the
 * platform runs English-only (founder, 2026-09-16), so the profile keeps ["en"].
 * On desktop the record beside the form re-sorts as the reader answers.
 */
const STEPS = ["Where you are", "What you do", "What you follow"] as const;
const LAST = STEPS.length - 1;

const H1 = { font: "var(--t-display-m)", letterSpacing: "var(--track-display)" } as const;
const LEDE = { font: "var(--t-body)", color: "var(--ink-2)" } as const;

const and = (names: string[]) => (names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}` : names[0] ?? "");

function OnboardingPage() {
  const router = useRouter();
  const taxonomy = useTaxonomy();
  const groups = useProfessionGroups();
  const regions = useRegions();
  const [step, setStep] = useState(0);
  const [state, setState] = useState("");
  const [lens, setLens] = useState("reader");
  const [picks, setPicks] = useState<Picks>({});
  const [preset, setPreset] = useState<string[]>([]);
  const [profession, setProfession] = useState<ProfessionOption | null>(null);
  const session = useSession();
  const [name, setName] = useState("");
  const [consent, setConsent] = useState(false);
  // Where the reader was going before sign-in interrupted (a gate, /plus).
  const next = safeNext(useSearchParams().get("next")) ?? "/feed";
  const [saving, setSaving] = useState(false);
  const [saveFailed, setSaveFailed] = useState(false);

  useEffect(() => {
    const existing = loadProfile();
    if (existing) {
      setLens(existing.lens);
      if (existing.state) setState(existing.state);
      setPicks(interestsToPicks(existing.interests));
    }
  }, []);

  function pickProfession(p: ProfessionOption) {
    const preSet = interestsToPicks(p.interests);
    setProfession(p);
    setLens(p.lens);
    setPicks(preSet);
    setPreset(SECTOR_GROUPS.filter((g) => groupOn(preSet, g.sectors)).map((g) => g.slug));
  }

  // The account needs all three; without them "Build my feed" waits and says why.
  const accountIncomplete = !!session && (!name.trim() || !profession || !consent);

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
    // once the reader is signed in, and only with all three answers and the consent
    // in hand (the button waits for the same; this is the check that matters). If
    // that fails the answers stay (in this browser and on screen) and the reader can
    // try again or skip — never trapped here.
    if (session && profession && name.trim() && consent) {
      setSaving(true);
      setSaveFailed(false);
      try {
        await setProfile(session, { name: name.trim(), profession: profession.slug, state: state || null, languages: ["en"], consent });
      } catch {
        setSaving(false);
        setSaveFailed(true);
        return;
      }
      setSaving(false);
    }
    router.push(next);
  }

  const covered = regions.filter((r) => r.covered);
  const rest = regions.filter((r) => !r.covered).sort((a, b) => a.name.localeCompare(b.name));
  const meta = lensMeta(lens);
  const presetNames = SECTOR_GROUPS.filter((g) => preset.includes(g.slug)).map((g) => g.name);

  const body = [
    <section key="where" className="grid gap-5">
      <div className="grid gap-1.5">
        <h1 className="text-balance" style={H1}>Which state are you in?</h1>
        <p style={LEDE}>Prism leads with news from your state, and your state becomes a scope on Today.</p>
      </div>
      {covered.length > 0 && (
        <div className="grid gap-2" role="group" aria-labelledby="covered-label">
          <p id="covered-label" className="p-field__label">Local coverage available</p>
          <div className="grid grid-cols-2 gap-2">
            {covered.map((s) => (
              <button key={s.code} type="button" className="p-chip min-h-11 min-w-0 justify-start" style={{ whiteSpace: "normal" }} aria-pressed={state === s.code} onClick={() => setState(state === s.code ? "" : s.code)}>
                {state === s.code && <Check size={14} />}
                {s.name}
              </button>
            ))}
          </div>
        </div>
      )}
      <SelectField
        label={covered.length ? "All states & UTs" : "Your state"}
        value={rest.some((r) => r.code === state) ? state : ""}
        onChange={setState}
        options={[{ value: "", label: "Choose a state" }, ...rest.map((s) => ({ value: s.code, label: s.name }))]}
      />
    </section>,
    <section key="what" className="grid gap-5">
      <div className="grid gap-1.5">
        <h1 className="text-balance" style={H1}>What do you do?</h1>
        <p style={LEDE}>It decides which reading opens first on a story that earns one.</p>
      </div>
      {session && <TextField label="Your name" value={name} onChange={setName} autoComplete="name" hint="For the account you are signed in to." />}
      <SelectField
        label="Profession"
        value={profession?.slug ?? ""}
        onChange={(v) => {
          const p = groups.flatMap((g) => g.options).find((o) => o.slug === v);
          if (p) pickProfession(p);
        }}
        placeholder="Choose your profession"
        groups={[...groups.map((g) => ({ label: g.group, options: g.options.map((o) => ({ value: o.slug, label: o.label })) }))]}
      />
      {profession && (
        <div className="grid gap-1.5 px-3.5 py-3" style={{ background: "var(--sunken)", borderRadius: "var(--r-control)" }}>
          <p className="flex flex-wrap items-center gap-2" style={{ font: "600 14px/1.3 var(--font-read)" }}>
            Reads as{" "}
            <span className={`p-lensdot p-l-${meta.slug}`}><i />{meta.short}</span>
          </p>
          {presetNames.length > 0 && (
            <p style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-2)" }}>
              {and(presetNames)} {presetNames.length > 1 ? "are" : "is"} ticked for you in the next step. You can untick {presetNames.length > 1 ? "them" : "it"}.
            </p>
          )}
        </div>
      )}
    </section>,
    <section key="follow" className="grid gap-5">
      <div className="grid gap-1.5">
        <h1 className="text-balance" style={H1}>What do you follow?</h1>
        <p style={LEDE}>Turn on a subject to pick its topics. Your record leads with these.</p>
      </div>
      <SubjectToggles taxonomy={taxonomy} picks={picks} onPicks={setPicks} preset={preset} />
      {session && (
        <Checkbox checked={consent} onChange={setConsent}>
          I agree to the <Link href="/terms" className="underline underline-offset-[3px]">Terms</Link> and to Prism creating an account for me and processing my email per the{" "}
          <Link href="/privacy" className="underline underline-offset-[3px]">privacy policy</Link>.
        </Checkbox>
      )}
      {step === LAST && accountIncomplete && (
        <p className="p-field__hint">Your name, a profession and your agreement above are needed to save the account. Or skip for now.</p>
      )}
    </section>,
  ][step];

  const actions = (
    <div className="flex items-center gap-2.5">
      {step > 0 && (
        <button type="button" onClick={() => setStep(step - 1)} className="p-btn p-btn--ghost">
          <ArrowLeft size={16} />
          Back
        </button>
      )}
      <span className="flex-1" />
      <button
        type="button"
        onClick={() => (step < LAST ? setStep(step + 1) : finish())}
        disabled={saving || (step === LAST && accountIncomplete)}
        aria-busy={saving || undefined}
        className="p-btn p-btn--primary p-btn--lg"
      >
        {saving ? "Saving…" : step < LAST ? "Continue" : "Build my feed"}
      </button>
    </div>
  );

  return (
    <div className="mx-auto w-full max-w-[1016px] px-[var(--gutter)] pb-[calc(96px+env(safe-area-inset-bottom))] pt-3 lg:pb-12 lg:pt-6">
      {/* Nothing blocks reading: the way out is on every step. */}
      <div className="flex justify-end">
        <button type="button" onClick={() => router.push(next)} className="p-btn p-btn--text">Skip for now</button>
      </div>
      <div className="grid lg:grid-cols-[minmax(0,560px)_minmax(0,400px)] lg:justify-center lg:gap-14">
        <div className="grid min-w-0 content-start gap-5">
          <StepIndicator steps={STEPS} current={step} onPick={(i) => i < step && setStep(i)} />
          {saveFailed && (
            <Alert tone="error" title="Your account could not be saved">
              Your answers are kept in this browser. Try again, or skip for now.
            </Alert>
          )}
          <div className="grid gap-5 lg:rounded-[var(--r-lg)] lg:border lg:bg-[var(--surface)] lg:p-7" style={{ borderColor: "var(--line)" }}>
            {body}
            <div className="fixed inset-x-0 bottom-0 z-40 border-t bg-[var(--paper)] px-[var(--gutter)] pb-[calc(16px+env(safe-area-inset-bottom))] pt-3 lg:static lg:bg-transparent lg:px-0 lg:pb-0 lg:pt-4" style={{ borderColor: "var(--line)" }}>
              {actions}
            </div>
          </div>
          <p className="text-center" style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)", overflowWrap: "anywhere" }}>
            {session ? `Signed in as ${session.email}` : "No account needed. Your profile lives in this browser."}
          </p>
        </div>
        <OnboardingPreview interests={picksToInterests(picks)} state={state || null} subjects={followedSubjects(picks).map((s) => s.group.name)} />
      </div>
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
