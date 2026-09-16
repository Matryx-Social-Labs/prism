"use client";

// The reservation form (shape brief §8): four fields on stationery — where you
// are, what you do, what you follow, the languages you read — shared by /you
// (all at once) and onboarding (one step at a time), so the two never drift.
// Each field is a label in the reading voice above a control on a hairline;
// helper text is prose, not mono. The one place colour appears is the lens a
// profession reads as, because that is a lens speaking.
//
// Picks stay in the pipeline's ten sectors ({ [sector]: null | subsectors[] })
// so picksToInterests and the feed's ?interests= contract are unchanged; the
// reader sees the six subjects, and a subject toggles every sector it groups.

import { useEffect, useState } from "react";
import { StateSelect, type Picks } from "@/components/ProfileEditor";
import { fetchProfessions, type ProfessionGroup, type ProfessionOption, type TaxonomySector } from "@/lib/api";
import { fetchLanguages, type LanguageOption } from "@/lib/session";
import { lensMeta } from "@/lib/lenses";
import { SECTOR_GROUPS } from "@/lib/sectors";

export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="rule-live py-6">
      <p className="text-[13.5px] font-medium" style={{ color: "var(--ink)" }}>{label}</p>
      {hint && <p className="mt-1 max-w-[52ch] text-[13.5px] leading-[1.55]" style={{ color: "var(--ink-muted)" }}>{hint}</p>}
      <div className="mt-3">{children}</div>
    </div>
  );
}

export function StateField({ value, onChange }: { value: string; onChange: (code: string) => void }) {
  return (
    <Field label="Where you are" hint="Prism leads with news from your state, then the rest of India.">
      <StateSelect value={value} onChange={onChange} />
    </Field>
  );
}

export function useLanguageOptions(): { options: LanguageOption[]; defaults: string[] } {
  const [o, setO] = useState<{ options: LanguageOption[]; defaults: string[] }>({ options: [], defaults: [] });
  useEffect(() => {
    fetchLanguages().then((r) => setO({ options: r.languages, defaults: r.default })).catch(() => {});
  }, []);
  return o;
}

/** Tap to add in preference order; the number is the rank. The last language cannot be removed. */
export function LanguagesField({ value, onChange, options }: { value: string[]; onChange: (v: string[]) => void; options: LanguageOption[] }) {
  if (options.length === 0) return null;
  const toggle = (code: string) => {
    if (value.includes(code)) {
      if (value.length === 1) return; // a reader always reads something
      onChange(value.filter((c) => c !== code));
    } else onChange([...value, code]);
  };
  return (
    <Field label="Languages you read" hint="Your first pick leads. Nothing is ever hidden: languages rank the chart, they never filter it.">
      <div className="flex flex-wrap gap-x-6 gap-y-2 border-b" style={{ borderColor: "var(--line)" }}>
        {options.map((l) => {
          const idx = value.indexOf(l.code);
          const sel = idx >= 0;
          return (
            <button key={l.code} type="button" onClick={() => toggle(l.code)} aria-pressed={sel}
              aria-label={`${l.name}${sel ? `, preference ${idx + 1}` : ""}`}
              className="flex min-h-[44px] items-baseline gap-2 border-b-2 px-0.5 text-[15px] transition-[border-color]"
              style={{ borderColor: sel ? "var(--ink)" : "transparent", color: sel ? "var(--ink)" : "var(--ink-muted)", marginBottom: -1 }}>
              {l.native}
              {sel && <span className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>{idx + 1}</span>}
            </button>
          );
        })}
      </div>
    </Field>
  );
}

export function useProfessionGroups(): ProfessionGroup[] {
  const [groups, setGroups] = useState<ProfessionGroup[]>([]);
  useEffect(() => {
    fetchProfessions().then(setGroups).catch(() => setGroups([]));
  }, []);
  return groups;
}

/**
 * A native select with the professions grouped, and beneath it the lens that
 * profession reads as — the one coloured mark on the form. `lens` may differ
 * from the profession's default when the reader set it elsewhere.
 */
export function ProfessionField({
  groups, profession, lens, onPick,
}: { groups: ProfessionGroup[]; profession: string | null; lens: string; onPick: (p: ProfessionOption) => void }) {
  const meta = lensMeta(lens);
  const all = groups.flatMap((g) => g.options);
  return (
    <Field label="What you do" hint="Your profession picks how stories are read for you: what is extracted, how the chart ranks, what the agent asks. Every other read stays one tap away.">
      <select
        value={profession ?? ""}
        onChange={(e) => { const p = all.find((o) => o.slug === e.target.value); if (p) onPick(p); }}
        aria-label="Your profession"
        className="h-12 w-full border px-4 text-[16px] outline-none"
        style={{ borderColor: "var(--line-strong)", background: "var(--bg-elevated)", color: profession ? "var(--ink)" : "var(--ink-muted)" }}
      >
        <option value="" disabled>Choose your profession…</option>
        {groups.map((g) => (
          <optgroup key={g.group} label={g.group}>
            {g.options.map((o) => <option key={o.slug} value={o.slug} style={{ color: "var(--ink)" }}>{o.label}</option>)}
          </optgroup>
        ))}
      </select>
      <p className="mt-3 flex items-baseline gap-2 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
        <span aria-hidden className="inline-block h-[7px] w-[7px] translate-y-[-1px] rounded-full" style={{ background: meta.color }} />
        <span>Reads as <span className="font-medium" style={{ color: "var(--ink)" }}>{meta.name}</span>: {meta.plain ?? meta.tagline}.</span>
      </p>
    </Field>
  );
}

function groupOn(picks: Picks, sectors: string[]): boolean {
  return sectors.some((s) => s in picks);
}

/** The six subjects as rows; a followed subject opens its sub-sectors beneath. */
export function SectorsField({ taxonomy, picks, onPicks }: { taxonomy: TaxonomySector[]; picks: Picks; onPicks: (p: Picks) => void }) {
  const toggleGroup = (sectors: string[]) => {
    const next = { ...picks };
    if (groupOn(picks, sectors)) for (const s of sectors) delete next[s];
    else for (const s of sectors) next[s] = null;
    onPicks(next);
  };
  const toggleSub = (sector: string, sub: string) => {
    const next = { ...picks };
    const cur = Array.isArray(next[sector]) ? [...(next[sector] as string[])] : [];
    const arr = cur.includes(sub) ? cur.filter((x) => x !== sub) : [...cur, sub];
    next[sector] = arr.length ? arr : null;
    onPicks(next);
  };
  return (
    <Field label="What you follow" hint="Follow nothing and the chart is everyone's. Follow a subject and For you appears; narrow it to the beats you actually read.">
      <ul>
        {SECTOR_GROUPS.map((g) => {
          const on = groupOn(picks, g.sectors);
          const subs = g.sectors.flatMap((s) => (taxonomy.find((t) => t.slug === s)?.subsectors ?? []).map((sub) => ({ sector: s, ...sub })));
          const nsubs = g.sectors.reduce((n, s) => n + (Array.isArray(picks[s]) ? (picks[s] as string[]).length : 0), 0);
          return (
            <li key={g.slug} className="rule-live">
              <button type="button" onClick={() => toggleGroup(g.sectors)} aria-pressed={on}
                className="flex min-h-[48px] w-full items-baseline gap-3 py-3 text-left">
                <span className="w-9 font-mono text-[12px] tracking-[0.06em]" style={{ color: on ? "var(--ink)" : "var(--ink-faint)" }}>{g.code}</span>
                <span className="text-[15.5px] font-medium" style={{ color: on ? "var(--ink)" : "var(--ink-muted)" }}>{g.name}</span>
                <span className="ml-auto font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-faint)" }}>
                  {on ? (nsubs ? `${nsubs} ${nsubs === 1 ? "beat" : "beats"}` : "following") : ""}
                </span>
              </button>
              {on && subs.length > 0 && (
                <div className="flex flex-wrap gap-2 pb-4 pl-12">
                  {subs.map((sub) => {
                    const cur = picks[sub.sector];
                    const sel = Array.isArray(cur) && cur.includes(sub.slug);
                    return (
                      <button key={`${sub.sector}:${sub.slug}`} type="button" onClick={() => toggleSub(sub.sector, sub.slug)} aria-pressed={sel}
                        className="border px-3 py-1.5 text-[13px] transition"
                        style={{ borderColor: sel ? "var(--ink)" : "var(--line-strong)", background: sel ? "var(--bg-sunken)" : "transparent", color: sel ? "var(--ink)" : "var(--ink-muted)" }}>
                        {sub.name}
                      </button>
                    );
                  })}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </Field>
  );
}
