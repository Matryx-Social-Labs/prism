// Client for the watchlist API (read-only follows of tickers/sectors). All
// calls are bearer-authenticated with the current session.

import { API_URL } from "@/lib/api";
import { authHeader, type Session } from "@/lib/session";

export interface WatchItem {
  id: string;
  kind: string; // ticker | sector
  value: string;
}

export interface WatchEvent {
  id: string;
  title: string;
  summary: string | null;
  sector: string | null;
  tickers: string[];
  catalyst: string | null;
  last_updated_at: string;
}

async function req(session: Session | null, path: string, init: RequestInit = {}) {
  const res = await fetch(`${API_URL}/api/v1/watchlist${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...authHeader(session), ...(init.headers ?? {}) },
  });
  if (!res.ok) throw new Error(`watchlist ${res.status}`);
  return res.json();
}

export async function getWatchlist(session: Session | null): Promise<WatchItem[]> {
  return (await req(session, "")).items;
}

export async function follow(session: Session | null, kind: string, value: string): Promise<WatchItem[]> {
  return (await req(session, "", { method: "POST", body: JSON.stringify({ kind, value }) })).items;
}

export async function unfollow(session: Session | null, kind: string, value: string): Promise<WatchItem[]> {
  const q = `?kind=${encodeURIComponent(kind)}&value=${encodeURIComponent(value)}`;
  return (await req(session, q, { method: "DELETE" })).items;
}

export async function watchlistEvents(session: Session | null): Promise<WatchEvent[]> {
  return (await req(session, "/events")).items;
}
