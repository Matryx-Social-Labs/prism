// Fails when any labelling-guide sentence is in the built site's public
// JavaScript (founder, 2026-09-23: "do not leak this to outsiders").
//
// The guides live in common/label_guides.py and reach a browser only through
// the API, for an applicant or a batch's own invite. The sentences to look for
// are read from that file, so this check can never drift from the guides:
// every run of plain ASCII 30+ characters long inside a string literal there,
// except each task's `question` — that is its name, which the labeller
// dashboard shows on purpose (lib/labeller KIND_QUESTION).
// Run after `next build`; reads .next/static, which is exactly what a browser
// can download.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const guides = readFileSync(new URL("../../common/label_guides.py", import.meta.url), "utf8");
const sentinels = new Set();
for (const [, literal] of guides.matchAll(/(?<!"question": )"([^"\n]{30,})"/g)) {
  for (const piece of literal.replace(/\*\*|==/g, "").split(/[^\x20-\x7e]+/)) {
    if (piece.trim().length >= 30) sentinels.add(piece.trim());
  }
}
if (sentinels.size < 50) {
  console.error(`check-no-guides: only ${sentinels.size} sentences read from label_guides.py — the file moved?`);
  process.exit(1);
}

const files = [];
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path);
    else if (name.endsWith(".js")) files.push(path);
  }
})(new URL("../.next/static", import.meta.url).pathname);

const leaks = [];
for (const file of files) {
  const js = readFileSync(file, "utf8");
  for (const s of sentinels) if (js.includes(s)) leaks.push(`${file}: ${s.slice(0, 60)}…`);
}
if (leaks.length) {
  console.error(`check-no-guides: ${leaks.length} guide sentence(s) in the public bundle:\n${leaks.slice(0, 20).join("\n")}`);
  process.exit(1);
}
console.log(`check-no-guides: ${sentinels.size} guide sentences, none in ${files.length} public files`);
