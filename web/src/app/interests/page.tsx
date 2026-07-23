"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  InterestChips,
  LensPills,
  StateSelect,
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
  const [state, setState] = useState("");
  const [lens, setLens] = useState("reader");
  const [picks, setPicks] = useState<Picks>({});
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    const existing = loadProfile();
    if (existing) {
      setLens(existing.lens);
      if (existing.state) setState(existing.state);
      setPicks(interestsToPicks(existing.interests));
    }
  }, []);

  function save() {
    saveProfile({ lens, region: "IN", state: state || null, interests: picksToInterests(picks) });
    router.push("/feed");
  }

  return (
    <div className="mx-auto max-w-[720px] px-5 pb-20 pt-9 sm:px-8">
      <h1 className="text-[30px] font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        Your Prism
      </h1>
      <p className="mt-2 text-sm" style={{ color: "var(--ink-muted)" }}>
        State, lens, and interests — everything your feed is built from. Stored only in this
        browser.
      </p>

      <SectionLabel>Your state</SectionLabel>
      <StateSelect value={state} onChange={setState} />

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
