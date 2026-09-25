"use client";

// The reservation form (shape brief §8): three fields on stationery — where you
// are, what you do, what you follow — shared by /you
// (all at once) and onboarding (one step at a time), so the two never drift.
// (Languages are not collected while the platform runs English-only, founder
// 2026-09-16; the profile keeps a default of ["en"].)
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
import { lensMeta } from "@/lib/lenses";
import { SECTOR_GROUPS } from "@/lib/sectors";

export function Field({ label, hint, flush = false, children }: { label: string; hint?: string; /** Kept for callers; the field's padding is uniform in the Spectrum world. */ flush?: boolean; children: React.ReactNode }) {
  void flush;
  return (
    <div className="field">
      <p className="field-label">{label}</p>
      {hint && <p className="field-hint">{hint}</p>}
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
        className="input"
        style={{ color: profession ? "var(--ink)" : "var(--ink-3)" }}
      >
        <option value="" disabled>Choose your profession…</option>
        {groups.map((g) => (
          <optgroup key={g.group} label={g.group}>
            {g.options.map((o) => <option key={o.slug} value={o.slug} style={{ color: "var(--ink)" }}>{o.label}</option>)}
          </optgroup>
        ))}
      </select>
      <p className="mt-3 flex items-baseline gap-2 text-[13.5px]" style={{ color: "var(--ink-2)" }}>
        <span aria-hidden className="inline-block h-2 w-2 translate-y-[-1px] rounded-full" style={{ background: meta.color }} />
        <span>Reads as <span className="font-semibold" style={{ color: "var(--ink)" }}>{meta.name}</span>: {meta.plain ?? meta.tagline}.</span>
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
      <ul className="flex flex-col gap-2">
        {SECTOR_GROUPS.map((g) => {
          const on = groupOn(picks, g.sectors);
          const subs = g.sectors.flatMap((s) => (taxonomy.find((t) => t.slug === s)?.subsectors ?? []).map((sub) => ({ sector: s, ...sub })));
          const nsubs = g.sectors.reduce((n, s) => n + (Array.isArray(picks[s]) ? (picks[s] as string[]).length : 0), 0);
          return (
            <li key={g.slug} className="row-card overflow-hidden" style={on ? { borderColor: "var(--accent)" } : undefined}>
              <button type="button" onClick={() => toggleGroup(g.sectors)} aria-pressed={on}
                className="flex min-h-[48px] w-full items-center gap-3 px-4 py-2.5 text-left">
                <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border" style={{ borderColor: on ? "var(--accent)" : "var(--line-strong)", background: on ? "var(--accent)" : "transparent" }} aria-hidden>
                  {on && <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="var(--on-accent)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 4 4L19 6" /></svg>}
                </span>
                <span className="text-[15px] font-medium" style={{ color: on ? "var(--ink)" : "var(--ink-2)" }}>{g.name}</span>
                <span className="ml-auto font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--ink-3)" }}>
                  {on ? (nsubs ? `${nsubs} ${nsubs === 1 ? "beat" : "beats"}` : "following") : g.code}
                </span>
              </button>
              {on && subs.length > 0 && (
                <div className="flex flex-wrap gap-2 border-t px-4 py-3" style={{ borderColor: "var(--line)" }}>
                  {subs.map((sub) => {
                    const cur = picks[sub.sector];
                    const sel = Array.isArray(cur) && cur.includes(sub.slug);
                    return (
                      <button key={`${sub.sector}:${sub.slug}`} type="button" onClick={() => toggleSub(sub.sector, sub.slug)} aria-pressed={sel} className="chip h-8 px-3 text-[13px]">
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
