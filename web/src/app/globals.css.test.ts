import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// next/font sets the Latin UI face and Indic siblings on <body>. A custom property is
// resolved where it is declared, so a :root --font-ui that references them
// computes to nothing and every reading-voice line silently falls back to the
// system sans. It shipped that way for two days; this pins the declaration to
// the body block.
describe("globals.css — the reading voice resolves", () => {
  const css = readFileSync(path.resolve(__dirname, "globals.css"), "utf8");
  const bodyBlock = css.slice(css.indexOf("\nbody {"), css.indexOf("}", css.indexOf("\nbody {")));

  it("declares --font-ui inside body, where next/font puts every UI face", () => {
    expect(bodyBlock).toMatch(/--font-ui:\s*var\(--font-ui-latin\)/);
    expect(bodyBlock).toMatch(/var\(--font-hind\)/);
  });

  it("does not declare --font-ui on :root", () => {
    const root = css.slice(css.indexOf(":root {"), css.indexOf("\n}", css.indexOf(":root {")));
    expect(root).not.toMatch(/--font-ui:/);
  });
});
