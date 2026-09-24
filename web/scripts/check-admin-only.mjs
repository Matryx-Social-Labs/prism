// Fails when the chart library reaches any page but /admin (founder decision
// V1, 2026-09-24): Recharts is ~130 kB, and a reader on a phone in a small
// town should never download a founder's dashboard.
//
// Reads what `next build` wrote: every route's chunks from
// .next/app-build-manifest.json, and in each chunk Recharts' own class names,
// which survive minification.

import { readFileSync } from "node:fs";

const MARK = "recharts-";
const pages = JSON.parse(readFileSync(".next/app-build-manifest.json", "utf8")).pages;
const charted = new Set(
  [...new Set(Object.values(pages).flat())].filter((f) => readFileSync(`.next/${f}`, "utf8").includes(MARK)),
);
if (charted.size === 0) {
  console.error("check-admin-only: no chunk carries Recharts — did /admin stop using it, or did the marker change?");
  process.exit(1);
}
const leaks = Object.entries(pages).filter(([route, files]) => !route.startsWith("/admin") && files.some((f) => charted.has(f)));
for (const [route] of leaks) console.error(`check-admin-only: ${route} loads the chart library`);
if (leaks.length) process.exit(1);
console.log(`check-admin-only: Recharts only under /admin (${charted.size} chunk${charted.size > 1 ? "s" : ""}).`);
