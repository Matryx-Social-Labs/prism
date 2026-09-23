// Fails when any labelling-guide sentence is in the built site's public
// JavaScript (founder, 2026-09-23: "do not leak this to outsiders").
//
// The guides live in common/label_guides.py and reach a browser only through
// the API, for an applicant or a batch's own invite. The sentences to look for
// are read from that file, so this check can never drift from the guides:
// every string literal there of 20 characters or more.
//
// Both sides are normalised before comparing — curly quotes, dashes and
// ellipses to plain ASCII, \uXXXX escapes decoded, whitespace collapsed — so a
// minifier escaping "—" cannot hide a sentence, and a short line dense with
// quotes ("NOT SURE — the article only says “the Collector”") is still one
// whole sentinel rather than fragments too short to count (review, 2026-09-23).
//
// The only strings exempted are the task names the labeller dashboard shows on
// purpose — read from lib/labeller.ts KIND_QUESTION itself, so the exemption
// covers exactly what is already public and nothing else.
//
// Run after `next build`; reads .next/static, which is what a browser can download.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const MIN_CHARS = 20;

const normalise = (s) =>
  s
    .replace(/\\u([0-9a-fA-F]{4})/g, (_, h) => String.fromCharCode(parseInt(h, 16)))
    .replace(/[“”„″]/g, '"')
    .replace(/[‘’′]/g, "'")
    .replace(/[—–]/g, "-")
    .replace(/…/g, "...")
    .replace(/\*\*|==/g, "")
    .replace(/\s+/g, " ")
    .trim();

const guides = readFileSync(new URL("../../common/label_guides.py", import.meta.url), "utf8");
const labeller = readFileSync(new URL("../src/lib/labeller.ts", import.meta.url), "utf8");
const kindQuestion = labeller.match(/KIND_QUESTION[^{]*\{([^}]*)\}/);
if (!kindQuestion) {
  console.error("check-no-guides: KIND_QUESTION not found in src/lib/labeller.ts — it moved?");
  process.exit(1);
}
const shown = new Set([...kindQuestion[1].matchAll(/"([^"]+)"/g)].map(([, q]) => normalise(q)));

const sentinels = new Set();
for (const [, literal] of guides.matchAll(/"([^"\n]{20,})"/g)) {
  const s = normalise(literal);
  if (s.length >= MIN_CHARS && !shown.has(s)) sentinels.add(s);
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
  const js = normalise(readFileSync(file, "utf8"));
  for (const s of sentinels) if (js.includes(s)) leaks.push(`${file}: ${s.slice(0, 60)}…`);
}
if (leaks.length) {
  console.error(`check-no-guides: ${leaks.length} guide sentence(s) in the public bundle:\n${leaks.slice(0, 20).join("\n")}`);
  process.exit(1);
}
console.log(`check-no-guides: ${sentinels.size} guide sentences, none in ${files.length} public files`);
