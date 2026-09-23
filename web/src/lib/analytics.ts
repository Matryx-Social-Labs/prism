// Usage counts, nothing about a person (admin dashboard, phase 3; founder
// decision D2): every call here becomes one daily count on our own API
// (api/routes/beacon.py, common/usage.py), with one word saying which kind —
// a kind of page, how Ask was opened, which step of subscribing. Never a
// story, never a question, never a name. No cookie is set; the privacy policy
// says exactly this ("What we collect").
//
// A signed-in reader's beacon carries their session so the API can note that
// they were active today — the day only, which is what retention is measured
// on. That is the one reason this uses fetch (sendBeacon cannot carry it).

import { API_URL } from "@/lib/api";
import { loadSession } from "@/lib/session";

type Props = Record<string, string | number | boolean | undefined>;
type Event = "Sign in" | "Ask" | "Lens" | "Subscribe" | "Share";

const NAME: Record<Event, string> = { "Sign in": "signin", Ask: "ask", Lens: "lens", Subscribe: "subscribe", Share: "share" };

/** The one word the API keeps for an event: lowercase, a short slug. The API
 *  checks it again against its own lists and drops anything else. */
export function word(...parts: Array<string | number | boolean | undefined>): string {
  return parts
    .filter((p) => p !== undefined && p !== "")
    .join(":")
    .toLowerCase()
    .replace(/[^a-z0-9:_.-]+/g, "-")
    .slice(0, 48);
}

function dimension(event: Event, p: Props): string {
  switch (event) {
    case "Lens":
      return word(p.lens, p.locked ? "locked" : "open");
    case "Subscribe":
      // The step, then what led there: the door (`from`), the reason chosen, or the plan.
      return word(p.stage, p.from ?? p.reason ?? p.plan);
    case "Ask":
      return word(p.via);
    case "Share":
      return word(p.surface ?? "other");
    case "Sign in":
      return word(p.method);
  }
}

/** Post one count. Fire-and-forget: a lost count never costs the reader anything. */
export function send(e: string, d: string, extra: Record<string, string> = {}): void {
  // Tests render components that count things; they must not reach a network.
  if (typeof window === "undefined" || process.env.NODE_ENV === "test") return;
  const token = loadSession()?.token;
  void fetch(`${API_URL}/api/v1/beacon`, {
    method: "POST",
    keepalive: true,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({ e, d, ...extra }),
  }).catch(() => undefined);
}

/** Count one action. The names are the handful above, so the dashboard stays readable. */
export function track(event: Event, props: Props = {}): void {
  send(NAME[event], dimension(event, props));
}

/** The kind of page a path is — the only thing a page view keeps. Mirrors
 *  common/usage.PAGES; a path not listed is "other". */
export function pageKind(path: string): string {
  if (path === "/") return "landing";
  const [, first = "", , third] = path.split("/");
  if (first === "story") return third === "quote" ? "quote" : "story";
  const kinds: Record<string, string> = {
    about: "about", feed: "feed", trending: "trending", subject: "subject", sector: "sector", entity: "entity",
    pulse: "pulse", search: "search", plus: "plus", account: "account", you: "account", watchlist: "account",
    interests: "account", onboarding: "account", signin: "signin", auth: "signin", label: "label",
    privacy: "legal", terms: "legal", refunds: "legal",
  };
  return kinds[first] ?? "other";
}

/** What a shared link points at, for the share count and the `?s=` marker. */
export function shareSurface(url: string): "story" | "quote" | "trending" | "other" {
  const kind = pageKind(url.replace(/^https?:\/\/[^/]+/, "").split("?")[0]);
  return kind === "story" || kind === "quote" || kind === "trending" ? kind : "other";
}
