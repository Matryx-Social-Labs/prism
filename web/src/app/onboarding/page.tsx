"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  InterestChips,
  LensCards,
  RegionGrid,
  interestsToPicks,
  picksToInterests,
  useTaxonomy,
  type Picks,
} from "@/components/ProfileEditor";
import { loadProfile, saveProfile } from "@/lib/profile";

const STEPS = ["Where you are", "How you read", "What you follow"] as const;

export default function OnboardingPage() {
  const router = useRouter();
  const taxonomy = useTaxonomy();
  const [step, setStep] = useState(0);
  const [region, setRegion] = useState("IN");
  const [lens, setLens] = useState("general");
  const [picks, setPicks] = useState<Picks>({});
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    const existing = loadProfile();
    if (existing) {
      setLens(existing.lens);
      if (existing.region) setRegion(existing.region);
      setPicks(interestsToPicks(existing.interests));
    }
  }, []);

  function finish() {
    saveProfile({ lens, region, interests: picksToInterests(picks) });
    router.push("/feed");
  }

  return (
    <div className="mx-auto max-w-[600px] px-5 pb-20 pt-9">
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
            Where do you read from?
          </h1>
          <p className="mt-2.5 text-sm leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
            Your feed blends international coverage with news from your region — and flags stories
            your region&apos;s outlets haven&apos;t covered yet.
          </p>
          <div className="mt-6">
            <RegionGrid value={region} onChange={setRegion} />
          </div>
        </section>
      )}

      {step === 1 && (
        <section>
          <h1 className="text-[32px] font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            How do you read the world?
          </h1>
          <p className="mt-2.5 text-sm leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
            Your lens sets the default read of each story. Every other applicable lens stays one
            tap away — switch anytime.
          </p>
          <div className="mt-6">
            <LensCards value={lens} onChange={setLens} />
          </div>
        </section>
      )}

      {step === 2 && (
        <section>
          <h1 className="text-[32px] font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            What do you follow?
          </h1>
          <p className="mt-2.5 text-sm leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
            Pick sectors, then narrow any of them to the sub-domains you actually care about
            (cricket, AI, elections…). Pick nothing and you get everything.
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
