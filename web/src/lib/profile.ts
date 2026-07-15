// Onboarding-lite profile persisted in localStorage: role lens, home
// region, and sector/sub-domain interests ("sports:cricket" or "politics").
// Replaced by real accounts + user_profiles when auth lands (roadmap 1.4).

export interface Profile {
  lens: string;
  region: string | null;
  interests: string[];
}

const KEY = "prism.profile.v1";

export function loadProfile(): Profile | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Profile>;
    if (!parsed.lens) return null;
    // migrate legacy {lens}-only profiles
    return { lens: parsed.lens, region: parsed.region ?? null, interests: parsed.interests ?? [] };
  } catch {
    return null;
  }
}

export function saveProfile(profile: Profile): void {
  window.localStorage.setItem(KEY, JSON.stringify(profile));
}
