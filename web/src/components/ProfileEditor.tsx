"use client";

// The pieces /you and onboarding share: the picks codec (and its toggles), the
// state select, and the six subjects as toggle rows. Picks: { [sector]: null (whole sector) |
// string[] (subsectors) } in the pipeline's ten sectors.

import { useEffect, useState } from "react";
import { SelectField, ToggleRow } from "@/components/ui";
import { fetchProfessions, fetchRegions, fetchTaxonomy, type ProfessionGroup, type RegionState, type TaxonomySector } from "@/lib/api";
import { SECTOR_GROUPS, type SectorGroup } from "@/lib/sectors";

export type Picks = Record<string, string[] | null>;

export function picksToInterests(picks: Picks): string[] {
  const out: string[] = [];
  for (const [sec, subs] of Object.entries(picks)) {
    if (!subs || subs.length === 0) out.push(sec);
    else for (const sub of subs) out.push(`${sec}:${sub}`);
  }
  return out;
}

export function interestsToPicks(interests: string[]): Picks {
  const picks: Picks = {};
  for (const token of interests) {
    const [sec, sub] = token.split(":");
    if (sub) {
      const cur = picks[sec];
      picks[sec] = Array.isArray(cur) ? [...cur, sub] : [sub];
    } else if (!(sec in picks)) {
      picks[sec] = null;
    }
  }
  return picks;
}

/** A subject is followed when any sector it groups is. */
export function groupOn(picks: Picks, sectors: string[]): boolean {
  return sectors.some((s) => s in picks);
}

/** Follow every sector a subject groups, or drop them all. */
export function toggleGroup(picks: Picks, sectors: string[]): Picks {
  const next = { ...picks };
  if (groupOn(picks, sectors)) for (const s of sectors) delete next[s];
  else for (const s of sectors) next[s] = null;
  return next;
}

/** Narrow a sector to a beat, or widen it back; no beats left means the whole sector. */
export function toggleSub(picks: Picks, sector: string, sub: string): Picks {
  const cur = Array.isArray(picks[sector]) ? (picks[sector] as string[]) : [];
  const arr = cur.includes(sub) ? cur.filter((x) => x !== sub) : [...cur, sub];
  return { ...picks, [sector]: arr.length ? arr : null };
}

export function useTaxonomy(): TaxonomySector[] {
  const [taxonomy, setTaxonomy] = useState<TaxonomySector[]>([]);
  useEffect(() => {
    fetchTaxonomy().then(setTaxonomy).catch(() => setTaxonomy([]));
  }, []);
  return taxonomy;
}

/** The states from /regions. A down API is an empty list, never an unhandled rejection. */
/** The professions, grouped, from the API; empty until they arrive (or if they cannot). */
export function useProfessionGroups(): ProfessionGroup[] {
  const [groups, setGroups] = useState<ProfessionGroup[]>([]);
  useEffect(() => {
    fetchProfessions().then(setGroups).catch(() => setGroups([]));
  }, []);
  return groups;
}

export function useRegions(): RegionState[] {
  const [states, setStates] = useState<RegionState[]>([]);
  useEffect(() => {
    fetchRegions().then(setStates).catch(() => setStates([]));
  }, []);
  return states;
}

const byName = (a: RegionState, b: RegionState) => a.name.localeCompare(b.name);

/** Every state and UT in one labelled select, "Not set" first so an empty value never shows as a state. */
export function StateSelect({ value, onChange, id, label = "State" }: { value: string; onChange: (code: string) => void; id?: string; label?: string }) {
  const list = [...useRegions()].sort(byName);
  return <SelectField id={id} label={label} value={value} onChange={onChange} options={[{ value: "", label: "Not set" }, ...list.map((s) => ({ value: s.code, label: s.name }))]} />;
}

/** The subjects a picks object follows, with how many of their beats are narrowed ("Business & Markets · 2 topics"). */
export function followedSubjects(picks: Picks): { group: SectorGroup; topics: number }[] {
  return SECTOR_GROUPS.filter((g) => groupOn(picks, g.sectors)).map((g) => ({
    group: g,
    topics: g.sectors.reduce((n, s) => n + (Array.isArray(picks[s]) ? (picks[s] as string[]).length : 0), 0),
  }));
}

/**
 * The six subjects as ToggleRows (Design System v2): turning one on follows every
 * sector it groups and opens its beats as chips; a chip narrows to that beat.
 * `preset` marks the subjects a profession ticked ("Pre-set from your profession").
 */
export function SubjectToggles({ taxonomy, picks, onPicks, preset = [] }: { taxonomy: TaxonomySector[]; picks: Picks; onPicks: (p: Picks) => void; preset?: readonly string[] }) {
  return (
    <div className="border-b" style={{ borderColor: "var(--line)" }}>
      {SECTOR_GROUPS.map((g) => {
        const subs = g.sectors.flatMap((s) => (taxonomy.find((t) => t.slug === s)?.subsectors ?? []).map((sub) => ({ sector: s, ...sub })));
        return (
          <ToggleRow
            key={g.slug}
            label={g.name}
            sub={preset.includes(g.slug) ? "Pre-set from your profession" : undefined}
            on={groupOn(picks, g.sectors)}
            onChange={() => onPicks(toggleGroup(picks, g.sectors))}
          >
            {subs.length > 0 &&
              subs.map((sub) => {
                const cur = picks[sub.sector];
                return (
                  <button
                    key={`${sub.sector}:${sub.slug}`}
                    type="button"
                    className="p-chip"
                    aria-pressed={Array.isArray(cur) && cur.includes(sub.slug)}
                    onClick={() => onPicks(toggleSub(picks, sub.sector, sub.slug))}
                  >
                    {sub.name}
                  </button>
                );
              })}
          </ToggleRow>
        );
      })}
    </div>
  );
}
