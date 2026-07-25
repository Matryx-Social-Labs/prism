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

// [code, native name, latin name]. Order in the profile is user-set; this is
// just the pickable set. Kept inline — no taxonomy endpoint for languages yet.
const LANGS: [string, string, string][] = [
  ["en", "English", ""],
  ["kn", "ಕನ್ನಡ", "Kannada"],
  ["hi", "हिंदी", "Hindi"],
  ["ta", "தமிழ்", "Tamil"],
  ["te", "తెలుగు", "Telugu"],
  ["bn", "বাংলা", "Bengali"],
  ["mr", "मराठी", "Marathi"],
];

function langLabel(code: string) {
  const m = LANGS.find(([c]) => c === code);
  if (!m) return code;
  const [, native, latin] = m;
  if (!latin) return native;
  return (
    <>
      {native}{" "}
      <span className="font-medium" style={{ color: "var(--ink-muted)" }}>
        {latin}
      </span>
    </>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2
      className="mb-2.5 mt-[30px] text-[11px] font-semibold uppercase tracking-[0.16em]"
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
  const [languages, setLanguages] = useState<string[]>(["en"]);

  useEffect(() => {
    const existing = loadProfile();
    if (existing) {
      setLens(existing.lens);
      if (existing.state) setState(existing.state);
      setPicks(interestsToPicks(existing.interests));
      if (existing.languages?.length) setLanguages(existing.languages);
    }
  }, []);

  // ponytail: up/down reorder instead of real drag-and-drop — the handle is
  // decorative. Swap to a DnD lib only if users actually need to drag.
  function moveLang(i: number, dir: number) {
    setLanguages((prev) => {
      const j = i + dir;
      if (j < 0 || j >= prev.length) return prev;
      const next = [...prev];
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });
  }
  function removeLang(i: number) {
    setLanguages((prev) => prev.filter((_, k) => k !== i));
  }
  function addLang(code: string) {
    if (!code) return;
    setLanguages((prev) => (prev.includes(code) ? prev : [...prev, code]));
  }

  const available = LANGS.filter(([c]) => !languages.includes(c));

  function save() {
    saveProfile({
      lens,
      region: "IN",
      state: state || null,
      interests: picksToInterests(picks),
      languages,
    });
    router.push("/feed");
  }

  return (
    <div className="mx-auto max-w-[640px] px-8 pb-24 pt-10">
      <h1 className="text-[30px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
        Your Parse
      </h1>
      <p className="mt-2 text-sm" style={{ color: "var(--ink-muted)" }}>
        State, languages, lens, and interests — everything your feed is built from. Stored only in
        this browser.
      </p>

      <SectionLabel>Your state</SectionLabel>
      <StateSelect value={state} onChange={setState} />

      <h2
        className="mb-1.5 mt-[30px] text-[11px] font-semibold uppercase tracking-[0.16em]"
        style={{ color: "var(--ink-faint)" }}
      >
        Languages you read
      </h2>
      <p className="mb-2.5 text-xs" style={{ color: "var(--ink-faint)" }}>
        Order sets preference — stories rank and localise to these, but nothing is ever hidden. Drag
        to reorder.
      </p>
      <div className="flex flex-col gap-2">
        {languages.map((code, i) => (
          <div
            key={code}
            className="flex items-center gap-3 rounded-[12px] border px-3.5 py-2.5"
            style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
          >
            <span aria-hidden className="text-[13px]" style={{ color: "var(--ink-faint)" }}>
              ⠿
            </span>
            <span
              className="text-[11px]"
              style={{ fontFamily: "var(--font-mono), monospace", color: "var(--ink-faint)" }}
            >
              {i + 1}
            </span>
            <span className="text-sm font-semibold">{langLabel(code)}</span>
            <div className="ml-auto flex items-center gap-1.5">
              <button
                onClick={() => moveLang(i, -1)}
                disabled={i === 0}
                aria-label="Move up"
                className="text-[11px] transition disabled:opacity-30"
                style={{ color: "var(--ink-faint)" }}
              >
                ▲
              </button>
              <button
                onClick={() => moveLang(i, 1)}
                disabled={i === languages.length - 1}
                aria-label="Move down"
                className="text-[11px] transition disabled:opacity-30"
                style={{ color: "var(--ink-faint)" }}
              >
                ▼
              </button>
              {i === 0 ? (
                <span className="text-[11px]" style={{ color: "var(--ink-faint)" }}>
                  primary
                </span>
              ) : (
                <button
                  onClick={() => removeLang(i)}
                  aria-label={`Remove ${code}`}
                  className="transition hover:opacity-70"
                  style={{ color: "var(--ink-faint)" }}
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        ))}
        {available.length > 0 && (
          <select
            value=""
            onChange={(e) => addLang(e.target.value)}
            aria-label="Add a language"
            className="rounded-[12px] border border-dashed px-3.5 py-2.5 text-[13px] font-semibold outline-none"
            style={{ borderColor: "var(--line-strong)", color: "var(--ink-faint)", background: "transparent" }}
          >
            <option value="" disabled>
              + Add a language
            </option>
            {available.map(([c, native, latin]) => (
              <option key={c} value={c} style={{ color: "var(--ink)" }}>
                {latin ? `${native} ${latin}` : native}
              </option>
            ))}
          </select>
        )}
      </div>

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
          className="flex-1 rounded-full py-[13px] text-center text-sm font-semibold transition hover:opacity-85"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          Save &amp; rebuild my feed →
        </button>
      </div>
    </div>
  );
}
