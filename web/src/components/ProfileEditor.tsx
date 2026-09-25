"use client";

// The profile's shape and the pieces shared by /you and onboarding that are
// not fields of the reservation form (components/ReservationForm.tsx): the
// picks codec (and its toggles) and the state select. Picks: { [sector]: null (whole sector) |
// string[] (subsectors) } in the pipeline's ten sectors.

import { useEffect, useState } from "react";
import { fetchRegions, fetchTaxonomy, type RegionState, type TaxonomySector } from "@/lib/api";

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

export function StateSelect({ value, onChange, id }: { value: string; onChange: (code: string) => void; /** For a visible <label htmlFor>. */ id?: string }) {
  const [states, setStates] = useState<RegionState[]>([]);
  useEffect(() => {
    // .catch matters as much here as on useTaxonomy above: without it a down
    // /api/v1/regions is an unhandled rejection AND the dropdown silently shows
    // nothing but its disabled placeholder, with no hint that anything failed.
    fetchRegions()
      .then(setStates)
      .catch(() => setStates([]));
  }, []);
  // Covered states (we have a local edition) first and marked, then the rest.
  const covered = states.filter((s) => s.covered);
  const rest = states.filter((s) => !s.covered);
  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      // The language select beside it is labelled; this one had no accessible
      // name at all, so a screen reader announced an unlabelled combobox.
      aria-label="Your state"
      className="input"
      style={{ color: value ? "var(--ink)" : "var(--ink-3)" }}
    >
      <option value="" disabled>
        Select your state…
      </option>
      {covered.length > 0 && (
        <optgroup label="Local coverage available">
          {covered.map((s) => (
            <option key={s.code} value={s.code} style={{ color: "var(--ink)" }}>
              {s.name}
            </option>
          ))}
        </optgroup>
      )}
      <optgroup label="All states & UTs">
        {rest.map((s) => (
          <option key={s.code} value={s.code} style={{ color: "var(--ink)" }}>
            {s.name}
          </option>
        ))}
      </optgroup>
    </select>
  );
}

