"use client";

import type { FeedItem } from "@/lib/api";
import { bandOrigins } from "@/lib/dateline";

// The desktop Search ledger rail (Parse Desktop.dc.html, SEARCH screen).
//
// Desktop /search is The Stone, the same grid the desktop Feed is built on: a
// 104px mono rail outside a 1240px field (104 + 32 + 1240 = 1376). This file is
// the rail; the field's desktop composition lives in the page as `lg:` classes
// on the SAME elements the phone renders, deliberately — see below.
//
// TWO THINGS THE MOCK DOES THAT THIS RAIL DOES NOT:
//
// 1. The full hint strip "↑↓ MOVE / ⏎ OPEN / ⌘⏎ IN LENS / ESC CLOSE". Only ESC
//    is wired on this page (it clears the box). Printing a hint for a key that
//    does nothing is the same class of lie as "No stories match" on a failed
//    request — the bug this screen already has a regression test for — so the
//    other three are not printed until something implements them.
//
// 2. Repeating anything the field already says. A search page cannot have two
//    trees: /search's suite asserts with singular getByText/getByRole, so a
//    second copy of a headline, of "Searching…" or of an error line fails those
//    tests (jsdom applies no CSS, so `hidden lg:block` still renders). That is
//    also why the field is one responsive tree rather than a SearchDesktop
//    sibling of the phone layout.
//
// What the rail carries instead is what desktop width is FOR (DESIGN.md, the
// width rule, 2026-07-25): the evidence a phone reader has to drill for —
// how many stories matched, how many outlets are behind them, where they were
// filed — ambient beside the results rather than a tap away.

export function SearchRail({ results }: { results: FeedItem[] }) {
  const sources = results.reduce((n, i) => n + (i.source_count || 0), 0);
  const filed = bandOrigins(results);

  return (
    <div
      className="hidden font-mono text-[10.5px] uppercase leading-[1.9] tracking-[0.08em] lg:block"
      style={{ color: "var(--ink-faint)" }}
    >
      <div>Esc clear</div>
      {results.length > 0 && (
        <div className="mt-4">
          <div style={{ color: "var(--ink-muted)" }}>
            {results.length} result{results.length === 1 ? "" : "s"}
          </div>
          <div>
            {sources} source{sources === 1 ? "" : "s"}
          </div>
          {filed && <div>{filed}</div>}
        </div>
      )}
    </div>
  );
}
