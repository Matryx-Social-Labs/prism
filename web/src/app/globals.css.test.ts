import { readFileSync } from "node:fs";
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
