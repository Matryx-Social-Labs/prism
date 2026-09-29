import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Public content is crawlable — by search engines and by the answer engines'
// CITING crawlers (OAI-SearchBot and ChatGPT-User, Claude-SearchBot and
// Claude-User, PerplexityBot), all under "*": being read and cited is the point
// of a record. The TRAINING crawlers are refused (founder decision 2026-09-22):
// they feed pretraining corpora, not answers, so blocking them forgoes no
// citation and no Search ranking — Google-Extended governs Gemini training, not
// Googlebot or AI Overviews — while Prism's own synthesis, the one thing here
// that is Prism's, stays out of the next foundation model's data. GPTBot and
// ClaudeBot joined the list 2026-09-29: OpenAI and Anthropic document both as
// their TRAINING crawlers (search and user fetches have their own agents), so
// the first list, which called them citing, broke the rule it was written for.
// A citing crawler stays in "*" rather than a named group: a named group
// replaces the "*" rules, and PRIVATE would have to be repeated in each. User-specific pages are not crawlable (nothing to
// index, and they need auth anyway); internal search results and the
// labelling tool are not pages. "/label" (no trailing slash) covers the
// labeller workspace and every batch under it — "/label/" left the workspace
// itself crawlable. "/admin" is the founders' dashboard. "/card/" is a page's
// share card in Instagram's shapes, for the founders to download: an image a
// crawler has no use for, and each one is rendered on request (Vercel CPU).
// "/go/" stays open: a platform's link preview follows the short link to its
// page's card, and X's respects robots.txt.
const PRIVATE = ["/account", "/signin", "/auth/", "/onboarding", "/interests", "/watchlist", "/you", "/search", "/label", "/admin", "/plus/welcome", "/card/"];
const TRAINING_CRAWLERS = ["Google-Extended", "CCBot", "Applebot-Extended", "Bytespider", "meta-externalagent", "GPTBot", "ClaudeBot"];

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
