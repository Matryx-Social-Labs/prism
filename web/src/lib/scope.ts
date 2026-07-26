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

export function loadScope(): Scope | null {
  if (typeof window === "undefined") return null; // SSR: caller keeps its default
  try {
    const v = window.localStorage.getItem(KEY);
    return v === "all" || v === "region" || v === "world" ? v : null;
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
