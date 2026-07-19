// Canonical site origin for absolute metadata (OpenGraph/Twitter/canonical/
// JSON-LD). Pin the vanity domain with NEXT_PUBLIC_SITE_URL; otherwise fall
// back to the Vercel deployment URL (present at build on Vercel), then localhost.
const raw =
  (typeof process !== "undefined" &&
    (process.env.NEXT_PUBLIC_SITE_URL ??
      (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : undefined))) ||
  "http://localhost:3000";

export const SITE_URL = raw.replace(/\/$/, "");
