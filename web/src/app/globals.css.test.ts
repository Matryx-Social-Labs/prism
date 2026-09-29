import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// A custom property resolves where it is declared. The voice stacks
// (--font-record/--font-read/--font-mono) and the type scale (--t-body: … var(--font-read))
// are generated onto :root, so the next/font family variables they reference must live on
// <html> — the same element. Put them on <body> and every stack on :root computes to
// nothing: the reading voice silently falls back to the system sans (it shipped that way
// for two days in September). This pins both halves.
describe("the three voices resolve", () => {
  const css = readFileSync(path.resolve(__dirname, "globals.css"), "utf8");
  const layout = readFileSync(path.resolve(__dirname, "layout.tsx"), "utf8");
  const root = css.slice(css.indexOf(":root,"), css.indexOf("\n}", css.indexOf(":root,")));

  it("declares the voice stacks and the type scale on :root", () => {
    expect(root).toMatch(/--font-read:\s*var\(--font-anek-latin\)/);
    expect(root).toMatch(/--font-record:\s*var\(--font-newsreader\)/);
    expect(root).toMatch(/--font-mono:\s*var\(--font-geist-mono\)/);
    expect(root).toMatch(/--t-body:\s*400 16px\/1\.6 var\(--font-read\)/);
  });

  it("puts every next/font variable on <html>, not <body>", () => {
    expect(layout).toMatch(/<html[^>]*className=\{FONT_VARIABLES\}/);
    expect(layout).not.toMatch(/<body[^>]*FONT_VARIABLES/);
  });
});

// A rail scrolls one way. `overflow-x: auto` silently computes `overflow-y` to auto too, so a
// rail with 1–12px of vertical overflow (the story tabs' underline, the sub-topic chips, a card
// rising in) became a two-axis scroller: a sideways swipe on a phone moved it diagonally, and
// the end of a rail handed the swipe to the page. Every horizontal scroller pins its own
// vertical axis and keeps its overscroll to itself.
describe("horizontal rails scroll one way", () => {
  const css = readFileSync(path.resolve(__dirname, "globals.css"), "utf8");
  const SRC = path.resolve(__dirname, "..");
  const walk = (dir: string): string[] =>
    readdirSync(dir).flatMap((name) => {
      const p = path.join(dir, name);
      if (statSync(p).isDirectory()) return walk(p);
      return name.endsWith(".tsx") && !name.includes(".test.") ? [p] : [];
    });

  it.each([".p-hide-scroll, .hide-scroll", ".sc-rail", ".sc-tabs"])("%s locks the vertical axis", (selector) => {
    const rule = css.match(new RegExp(`^${selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*\\{([^}]*)\\}`, "m"))?.[1];
    expect(rule, `no rule for ${selector}`).toBeDefined();
    expect(rule).toMatch(/overflow-y:\s*hidden/);
    expect(rule).toMatch(/overscroll-behavior-x:\s*contain/);
  });

  it("every overflow-x-auto class list is a rail or pins overflow-y", () => {
    const loose = walk(SRC).flatMap((file) =>
      (readFileSync(file, "utf8").match(/["'`][^"'`]*\boverflow-x-auto\b[^"'`]*["'`]/g) ?? [])
        .filter((cls) => !/\b(p-)?hide-scroll\b|\boverflow-y-hidden\b/.test(cls))
        .map((cls) => `${path.relative(SRC, file)}: ${cls}`),
    );
    expect(loose).toEqual([]);
  });
});
