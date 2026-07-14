// Onboarding-lite profile: role lens choice persisted in localStorage.
// Replaced by real accounts + user_profiles when auth lands (roadmap 1.4).

export interface Profile {
  lens: string;
}

const KEY = "prism.profile.v1";

export function loadProfile(): Profile | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Profile;
    return parsed.lens ? parsed : null;
  } catch {
    return null;
  }
}

export function saveProfile(profile: Profile): void {
  window.localStorage.setItem(KEY, JSON.stringify(profile));
}
