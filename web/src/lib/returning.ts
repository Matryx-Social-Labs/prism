/**
 * Anyone who has reached the chart once has seen the product, so `/` takes
 * them straight back to it next time instead of the landing (app/page.tsx
 * reads this cookie server-side). One byte, no token — the session stays in
 * localStorage where it always was. A plain module, not part of a "use client"
 * file, so the server page can import the name.
 */
export const RETURNING_COOKIE = "prism.returning";

export function markReturning() {
  try {
    document.cookie = `${RETURNING_COOKIE}=1; path=/; max-age=31536000; samesite=lax`;
  } catch {
    /* cookies disabled: the landing shows again, which is harmless */
  }
}
