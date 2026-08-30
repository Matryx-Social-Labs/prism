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
