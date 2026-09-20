import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Public content is crawlable — by search engines and by the answer engines'
// crawlers alike (GPTBot, ClaudeBot, PerplexityBot, Google-Extended…): being
// read and cited is the point of a record. User-specific pages are not
// (nothing to index, and they need auth anyway); internal search results and
// the labelling tool are not pages.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // "/you" folds account + interests + watchlist into one hub and renders the
      // signed-in email, so it belongs alongside its siblings here.
      disallow: ["/account", "/signin", "/auth/", "/onboarding", "/interests", "/watchlist", "/you", "/search", "/label/", "/plus/welcome"],
    },
    sitemap: [`${SITE_URL}/sitemap.xml`, `${SITE_URL}/news-sitemap.xml`],
    host: SITE_URL,
  };
}
