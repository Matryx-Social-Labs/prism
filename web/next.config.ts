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
};

export default nextConfig;
