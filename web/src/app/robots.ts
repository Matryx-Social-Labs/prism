import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Public content is crawlable — by search engines and by the answer engines'
// CITING crawlers (GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot): being read
// and cited is the point of a record. The TRAINING-only crawlers are refused
// (founder decision 2026-09-22): they feed pretraining corpora, not answers,
// so blocking them forgoes no citation and no Search ranking — Google-Extended
// governs Gemini training, not Googlebot or AI Overviews — while Prism's own
// synthesis, the one thing here that is Prism's, stays out of the next
// foundation model's data. User-specific pages are not crawlable (nothing to
// index, and they need auth anyway); internal search results and the
// labelling tool are not pages. "/label" (no trailing slash) covers the
// labeller workspace and every batch under it — "/label/" left the workspace
// itself crawlable. "/admin" is the founders' dashboard.
const PRIVATE = ["/account", "/signin", "/auth/", "/onboarding", "/interests", "/watchlist", "/you", "/search", "/label", "/admin", "/plus/welcome"];
const TRAINING_CRAWLERS = ["Google-Extended", "CCBot", "Applebot-Extended", "Bytespider", "meta-externalagent"];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      // "/you" folds account + interests + watchlist into one hub and renders the
      // signed-in email, so it belongs alongside its siblings here.
      { userAgent: "*", allow: "/", disallow: PRIVATE },
      ...TRAINING_CRAWLERS.map((userAgent) => ({ userAgent, disallow: "/" })),
    ],
    sitemap: [`${SITE_URL}/sitemap.xml`, `${SITE_URL}/news-sitemap.xml`, `${SITE_URL}/records-sitemap.xml`, `${SITE_URL}/entities-sitemap.xml`],
    host: SITE_URL,
  };
}
