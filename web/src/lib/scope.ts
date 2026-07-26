"use client";

// Where the reader wants their news from, shared across surfaces and persisted.
//
// This used to be per-page component state seeded from the profile on every
// mount, which meant picking "World" and reloading silently snapped you back to
// your state — the choice never outlived the page. It also made the scope
// sheet's "Applies everywhere" line untrue.
//
// Kept in localStorage next to the profile rather than inside it: scope is a
// view preference the reader flips several times a session, not part of their
// identity, and writing it shouldn't churn the profile object the feed query
// depends on.

export type Scope = "all" | "region" | "world";

const KEY = "parse.scope.v1";

/**
 * `hasState` — whether the reader currently has a state on their profile.
 *
 * Scope and profile live under separate keys, so they can drift: pick "Your
 * state", later clear the state in your profile, and the saved scope outlives
 * the thing it referred to. The chip then reads "Your state" while the feed is
 * actually unfiltered — a label naming a filter that isn't applied, and the
 * sheet's own option is disabled so the reader can't correct it.
 *
 * Both "region" AND "world" are state-relative on the Feed: region is my state,
 * world is "National" — everything that is NOT my state. Neither means anything
 * without one, and the Feed's filter short-circuits on `!profile.state`. So a
 * stateless reader who picked National on Trending (enabled there, because
 * Trending's National is absolute) walked back to a Feed labelled "National"
 * over unfiltered stories with the option greyed out. Only "all" — the whole
 * world, no tiering — still means something with no state.
 *
 * Nulling "world" costs Trending nothing: its own default is already "world",
 * so a stateless reader still lands on National, just not via a stored value.
 */
export function loadScope(hasState = true): Scope | null {
  if (typeof window === "undefined") return null; // SSR: caller keeps its default
  try {
    const v = window.localStorage.getItem(KEY);
    if (v !== "all" && v !== "region" && v !== "world") return null;
    if (!hasState && v !== "all") return null;
    return v;
  } catch {
    return null; // storage blocked (in-app webviews) — scope just won't persist
  }
}

export function saveScope(scope: Scope): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(KEY, scope);
  } catch {
    /* not worth a crash */
  }
}
