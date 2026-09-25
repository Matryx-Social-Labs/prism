import type { NextConfig } from "next";

// The Content-Security-Policy, REPORT-ONLY first (audit H4): a wrong allowance
// breaks sign-in or checkout silently, so it reports to the API for a while
// before anything is enforced. Every origin here is one the browser really
// loads: Google's sign-in script and frame, Razorpay's checkout script, frames
// and calls, publishers' photographs and podcast audio (any https host), and
// our API. Next.js inlines its RSC payload, so script-src keeps 'unsafe-inline'
// until nonces are wired; the report still catches any unexpected host.
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' https://accounts.google.com https://checkout.razorpay.com",
  "style-src 'self' 'unsafe-inline' https://accounts.google.com",
  "img-src 'self' data: blob: https:",
  "media-src 'self' https:",
  "font-src 'self' data:",
  `connect-src 'self' ${API} https://accounts.google.com https://api.razorpay.com https://lumberjack.razorpay.com`,
  "frame-src https://accounts.google.com https://api.razorpay.com https://checkout.razorpay.com",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
  // `next dev` evaluates code (React refresh) and would report every page load;
  // a dev server pointed at the production API must not fill its report log.
  ...(process.env.NODE_ENV === "development" ? [] : [`report-uri ${API}/api/v1/csp-report`]),
].join("; ");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  images: {
    // Thumbnails come from arbitrary news CDNs discovered at ingest time. Vercel's
    // server-side optimizer gets blocked by those CDNs (datacenter IP / hotlink
    // protection) and 404s every thumbnail — so serve them directly from the
    // browser (which the CDNs allow: real UA + referer). onError hides the few that
    // still fail. Trade-off: no server resize, but 92–120px news JPGs are small.
    unoptimized: true,
    remotePatterns: [{ protocol: "https", hostname: "**" }],
  },
  async headers() {
    return [
      {
        // Every page. No framing (the account page's cancel and refund are one
        // click each — an overlay on a framed page would be a clickjack), no MIME
        // sniffing, a year of HSTS, and the browser features the site never uses
        // switched off, and the CSP in report-only mode (above).
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(self)" },
          { key: "Content-Security-Policy-Report-Only", value: CSP },
        ],
      },
      {
        // Defence in depth for the labelling surface. The credential is already
        // kept out of the URL and sent in a header, so there is nothing in the
        // address bar worth leaking — but a labelling link gets pasted into chat
        // apps and opened beside other tabs, and `no-referrer` means the batch key
        // is not announced to any third party the page happens to reach.
        source: "/label/:path*",
        headers: [{ key: "Referrer-Policy", value: "no-referrer" }],
      },
    ];
  },
};

export default nextConfig;
