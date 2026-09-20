// Where a reader was going when a gate (sign in, Plus) interrupted them. The
// path travels three ways, because sign-in has three exits: the `?next=` query
// (Google, same tab), the magic-link email (a NEW tab, so the server puts it in
// the link), and this tab's sessionStorage as the fallback for both. Only a
// same-site path is ever honoured — never a URL — so a link cannot send a
// reader off the site after they sign in.
const KEY = "prism.next.v1";

export function safeNext(value: string | null | undefined): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.length > 500) return null;
  return value;
}

export function rememberNext(value: string | null | undefined): void {
  const v = safeNext(value);
  try {
    if (v) window.sessionStorage.setItem(KEY, v);
  } catch {
    /* blocked storage: the query string still carries it */
  }
}

/** The remembered destination (cleared on read), or `fallback`. */
export function takeNext(fallback = "/feed", fromQuery?: string | null): string {
  const q = safeNext(fromQuery);
  let stored: string | null = null;
  try {
    stored = safeNext(window.sessionStorage.getItem(KEY));
    window.sessionStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
  return q ?? stored ?? fallback;
}

/** Where to send a new reader: onboarding first, then on to `next`. */
export function afterSignIn(needsProfile: boolean, next: string): string {
  return needsProfile ? `/onboarding?next=${encodeURIComponent(next)}` : next;
}
