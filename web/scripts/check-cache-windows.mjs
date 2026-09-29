// Every cached route refreshes on the clock it declares (caching plan,
// 2026-09-27). Next 15 re-renders a route at its SHORTEST fetch `revalidate`,
// so a page's own setting can be silently undercut: both sitemaps declared an
// hour and fifteen minutes and re-rendered every minute, because they read the
// feed at the feed's 60 s. A route missing from the manifest is rendered on
// every request — /about was, as force-dynamic.
//
// Reads what `next build` wrote: .next/prerender-manifest.json.

import { readFileSync } from "node:fs";

const EXPECTED = {
  "/feed": 60,
  "/sector/politics": 60,
  "/trending": 120,
  "/about": 60,
  "/sources": 300,
  "/corrections": 300,
  "/sitemap.xml": 3600,
};

const { routes } = JSON.parse(readFileSync(".next/prerender-manifest.json", "utf8"));
const wrong = Object.entries(EXPECTED).filter(([route, want]) => routes[route]?.initialRevalidateSeconds !== want);
for (const [route, want] of wrong) {
  const got = routes[route]?.initialRevalidateSeconds;
  console.error(`check-cache-windows: ${route} refreshes ${got ? `every ${got}s` : "on every request"}, expected every ${want}s`);
}
if (wrong.length) process.exit(1);
console.log(`check-cache-windows: ${Object.keys(EXPECTED).length} routes on their declared clocks.`);
