// Onboarding-lite profile persisted in localStorage: role lens, home
// region, and sector/sub-domain interests ("sports:cricket" or "politics").
// Replaced by real accounts + user_profiles when auth lands (roadmap 1.4).

export interface Profile {
  lens: string;
  region: string | null;
  state: string | null; // ISO 3166-2 (e.g. IN-KA) — surfaces local news first
  interests: string[];
  // ponytail: UI + localStorage only for now — feed ranking/localisation wiring deferred.
  languages?: string[]; // preference order, first = primary
}

const KEY = "prism.profile.v1";

export function loadProfile(): Profile | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Profile>;
    if (!parsed.lens) return null;
    // migrate legacy profiles (pre-state)
    return {
      lens: parsed.lens,
      region: parsed.region ?? null,
      state: parsed.state ?? null,
      interests: parsed.interests ?? [],
      languages: parsed.languages?.length ? parsed.languages : ["en"],
    };
  } catch {
    return null;
  }
}

export function saveProfile(profile: Profile): void {
  window.localStorage.setItem(KEY, JSON.stringify(profile));
}
