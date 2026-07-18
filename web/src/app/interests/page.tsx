"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  InterestChips,
  LensPills,
  RegionGrid,
  interestsToPicks,
  picksToInterests,
  useTaxonomy,
  type Picks,
} from "@/components/ProfileEditor";
import { loadProfile, saveProfile } from "@/lib/profile";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2
      className="mb-2.5 mt-[30px] text-[11px] font-semibold uppercase tracking-widest"
      style={{ color: "var(--ink-faint)" }}
    >
      {children}
    </h2>
  );
}

export default function InterestsPage() {
  const router = useRouter();
  const taxonomy = useTaxonomy();
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

  function save() {
    saveProfile({ lens, region, interests: picksToInterests(picks) });
    router.push("/feed");
  }

  return (
    <div className="mx-auto max-w-[600px] px-5 sm:px-8 pb-20 pt-9">
      <h1 className="text-[30px] font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        Your Prism
      </h1>
      <p className="mt-2 text-sm" style={{ color: "var(--ink-muted)" }}>
        Region, lens, and interests — everything your feed is built from. Stored only in this
        browser.
      </p>

      <SectionLabel>Where you read from</SectionLabel>
      <RegionGrid value={region} onChange={setRegion} />

      <SectionLabel>Your default lens</SectionLabel>
      <LensPills value={lens} onChange={setLens} />

      <SectionLabel>What you follow</SectionLabel>
      <InterestChips
        taxonomy={taxonomy}
        picks={picks}
        expanded={expanded}
        onPicks={setPicks}
        onExpanded={setExpanded}
      />

      <div className="mt-[34px] flex gap-3">
        <button
          onClick={() => router.push("/feed")}
          className="rounded-full border px-6 py-[13px] text-sm font-semibold"
          style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
        >
          Cancel
        </button>
        <button
          onClick={save}
          className="flex-1 rounded-full px-7 py-[13px] text-sm font-semibold transition hover:opacity-85"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          Save &amp; rebuild my feed →
        </button>
      </div>
    </div>
  );
}
