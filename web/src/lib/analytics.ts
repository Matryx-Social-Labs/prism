// Aggregate usage counts, nothing about a person. Plausible: no cookies, no
// cross-site id, no personal data — which is what the privacy policy promises,
// so never put a question, an email or a name in `props`. Off entirely until
// NEXT_PUBLIC_PLAUSIBLE_DOMAIN is set (pin it in ci.yml's "Inject public build
// env" step too, see lib/site.ts); until then `track` is a no-op.
export const PLAUSIBLE_DOMAIN = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN ?? "";

type Props = Record<string, string | number | boolean>;

declare global {
  interface Window {
    plausible?: (event: string, opts?: { props?: Props }) => void;
  }
}

/** Count one event. Names are the handful below, so the dashboard stays readable. */
export function track(event: "Sign in" | "Ask" | "Lens" | "Subscribe", props?: Props): void {
  if (typeof window === "undefined") return;
  window.plausible?.(event, props ? { props } : undefined);
}
