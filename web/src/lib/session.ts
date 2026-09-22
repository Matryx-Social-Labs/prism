"use client";

// Bearer session from magic-link auth, persisted in localStorage (mirrors
// lib/profile.ts). The raw bearer token lives only here and in the
// Authorization header; the server stores only its SHA-256 hash. Email
// delivery is server-side and pluggable — in dev the sign-in link is printed
// to the API logs (console sender), so the flow works with no email provider.

import { track } from "@/lib/analytics";
import { useEffect, useState } from "react";

import { API_URL } from "@/lib/api";

export interface Session {
  token: string;
  userId: string;
  email: string;
}

const KEY = "prism.session.v1";
const EVENT = "prism-session";

export function loadSession(): Session | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const p = JSON.parse(raw) as Partial<Session>;
    return p.token && p.userId && p.email
      ? { token: p.token, userId: p.userId, email: p.email }
      : null;
  } catch {
    return null;
  }
}

export function saveSession(s: Session): void {
  window.localStorage.setItem(KEY, JSON.stringify(s));
  window.dispatchEvent(new Event(EVENT));
}

export function clearSession(): void {
  const token = loadSession()?.token;
  window.localStorage.removeItem(KEY);
  window.dispatchEvent(new Event(EVENT));
  // Revoke server-side too: the row is gone, so the token is dead now rather
  // than at its 30-day expiry. Fire-and-forget — the local sign-out is the UX.
  if (token) {
    void fetch(`${API_URL}/api/v1/auth/session`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
      keepalive: true,
    }).catch(() => undefined);
  }
}

/** Authorization header for gated calls (pro lenses, watchlist, personalized brief). */
export function authHeader(session: Session | null): Record<string, string> {
  return session ? { Authorization: `Bearer ${session.token}` } : {};
}

async function detail(res: Response, fallback: string): Promise<string> {
  try {
    const d = (await res.json()) as { detail?: string };
    return d.detail ?? fallback;
  } catch {
    return fallback;
  }
}

/** Email-first: we always send a link (same response for new + returning readers,
 * so an onlooker can't tell whether an email is registered). The profile is
 * collected after verify, so this call needs nothing but an email. */
export async function requestMagicLink(email: string, next?: string | null): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/auth/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, next: next ?? undefined }),
  });
  if (!res.ok) throw new Error(await detail(res, "Could not send the sign-in link"));
}

export interface ProfessionGroup {
  group: string;
  options: { slug: string; label: string }[];
}

export async function fetchProfessions(): Promise<ProfessionGroup[]> {
  const res = await fetch(`${API_URL}/api/v1/professions`);
  if (!res.ok) return [];
  return ((await res.json()) as { groups: ProfessionGroup[] }).groups;
}

export interface LanguageOption {
  code: string;
  name: string;
  native: string;
}

export async function fetchLanguages(): Promise<{ languages: LanguageOption[]; default: string[] }> {
  const res = await fetch(`${API_URL}/api/v1/languages`);
  if (!res.ok) return { languages: [], default: [] };
  return (await res.json()) as { languages: LanguageOption[]; default: string[] };
}

export interface VerifyResult {
  session: Session;
  needsProfile: boolean;
}

export async function verifyMagicLink(token: string): Promise<VerifyResult> {
  const res = await fetch(`${API_URL}/api/v1/auth/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!res.ok) throw new Error(await detail(res, "This sign-in link is invalid or expired"));
  const d = (await res.json()) as {
    token: string;
    user_id: string;
    email: string;
    needs_profile: boolean;
  };
  track("Sign in", { method: "link" });
  return {
    session: { token: d.token, userId: d.user_id, email: d.email },
    needsProfile: d.needs_profile,
  };
}

/** A Google OAuth access token (from our button's token flow) → the same session a magic link gives. */
export async function signInWithGoogle(accessToken: string): Promise<VerifyResult> {
  const res = await fetch(`${API_URL}/api/v1/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ access_token: accessToken }),
  });
  if (!res.ok) throw new Error(await detail(res, "Google sign-in failed"));
  const d = (await res.json()) as { token: string; user_id: string; email: string; needs_profile: boolean };
  track("Sign in", { method: "google" });
  return { session: { token: d.token, userId: d.user_id, email: d.email }, needsProfile: d.needs_profile };
}

/** Who the session belongs to and the plan it is on (`plan`: free | plus). */
export async function fetchMe(session: Session): Promise<{ user_id: string; email: string; plan: "free" | "plus" | string }> {
  const res = await fetch(`${API_URL}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${session.token}` }, cache: "no-store" });
  if (!res.ok) throw new Error(`me ${res.status}`);
  return res.json();
}

/** The session's plan, "free" until known; anonymous is "free". Cached per
 * token for the tab so the header does not ask on every route. */
const planCache = new Map<string, "free" | "plus">();
export function usePlan(session: Session | null): "free" | "plus" {
  const [plan, setPlan] = useState<"free" | "plus">(session ? planCache.get(session.token) ?? "free" : "free");
  useEffect(() => {
    if (!session) return setPlan("free");
    const cached = planCache.get(session.token);
    if (cached) return setPlan(cached);
    let live = true;
    fetchMe(session)
      .then((m) => {
        const p = m.plan === "plus" ? "plus" : "free";
        planCache.set(session.token, p);
        if (live) setPlan(p);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [session]);
  return plan;
}

/** Complete onboarding for the signed-in reader (name, profession, location,
 * languages ordered by preference, consent). Requires a verified session. */
export async function setProfile(
  session: Session,
  body: { name: string; profession: string; state: string | null; languages: string[]; consent: boolean },
): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/auth/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(session) },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await detail(res, "Could not save your profile"));
}

/** Reactive session: re-reads on sign-in/out (same tab) and on storage (other tabs). */
export function useSession(): Session | null {
  const [session, setSession] = useState<Session | null>(null);
  useEffect(() => {
    const sync = () => setSession(loadSession());
    sync();
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  return session;
}
