import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Public content is crawlable; user-specific pages are not (nothing to index and
// they need auth anyway).
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/account", "/signin", "/auth/", "/onboarding", "/interests", "/watchlist"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
