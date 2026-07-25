import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Public content is crawlable; user-specific pages are not (nothing to index and
// they need auth anyway).
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // "/you" folds account + interests + watchlist into one hub and renders the
      // signed-in email, so it belongs alongside its siblings here.
      disallow: ["/account", "/signin", "/auth/", "/onboarding", "/interests", "/watchlist", "/you"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
