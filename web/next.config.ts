import type { NextConfig } from "next";

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
        // switched off. A Content-Security-Policy is deliberately absent: Google
        // sign-in, Razorpay checkout, Plausible and the inline JSON-LD each need
        // an allowance, and a wrong one breaks sign-in silently — it lands
        // report-only first, once there is somewhere for the reports to go.
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(self)" },
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
