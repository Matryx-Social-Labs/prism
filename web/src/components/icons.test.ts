import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// A text arrow renders in whatever face the fallback stack finds and reads as
// costume; the stroke icon is the same ink at every size (icons.tsx, DESIGN.md).
// The audit (2026-09-27) found "Their report ↗" and "Open at the quote ↗".
describe("the out-link arrow is an icon, never a glyph", () => {
  it("no source file prints ↗ as text", () => {
    const src = path.resolve(__dirname, "..");
    const files = readdirSync(src, { recursive: true, encoding: "utf8" })
      .filter((f) => /\.tsx?$/.test(f) && !/\.test\.tsx?$/.test(f) && !f.endsWith("icons.tsx"));
    expect(files.filter((f) => readFileSync(path.join(src, f), "utf8").includes("↗"))).toEqual([]);
  });
});
