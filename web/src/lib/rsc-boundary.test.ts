import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * REGRESSION: the landing (a server component) called `indexSources()` and
 * `coverageText()` imported from "use client" modules. In React Server
 * Components a function imported across that boundary is a reference, not a
 * function; calling it throws at render — and jsdom, which runs every other
 * test here, does not enforce the boundary. `/` for a first visitor and
 * `/about` returned 500 for two days (2026-09-18 → 20) with the suite green.
 *
 * This walks every .tsx that is NOT "use client" and checks that what it
 * imports from a "use client" module is a component (PascalCase) or a type —
 * never a lower-case function to call. Helpers a server component needs live
 * in lib/ (lib/coverage.ts, lib/sources.ts).
 */
const SRC = resolve(__dirname, "..");

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) return walk(p);
    return /\.(tsx|ts)$/.test(name) && !/\.test\.tsx?$/.test(name) ? [p] : [];
  });
}

const isClient = (file: string) => /^\s*["']use client["']/.test(readFileSync(file, "utf8"));

function resolveImport(spec: string): string | null {
  if (!spec.startsWith("@/")) return null;
  const base = join(SRC, spec.slice(2));
  for (const cand of [`${base}.tsx`, `${base}.ts`, join(base, "index.tsx"), join(base, "index.ts")]) {
    try {
      statSync(cand);
      return cand;
    } catch {
      /* next */
    }
  }
  return null;
}

describe("the server/client boundary", () => {
  it("no server component calls a function it imported from a 'use client' module", () => {
    const offences: string[] = [];
    for (const file of walk(SRC)) {
      if (!file.endsWith(".tsx") || isClient(file)) continue;
      const src = readFileSync(file, "utf8");
      for (const m of src.matchAll(/import\s*\{([^}]*)\}\s*from\s*["']([^"']+)["']/g)) {
        const target = resolveImport(m[2]);
        if (!target || !isClient(target)) continue;
        for (const raw of m[1].split(",")) {
          const name = raw.trim().replace(/^type\s+/, "").split(/\s+as\s+/)[0].trim();
          if (!name || raw.trim().startsWith("type ")) continue;
          if (/^[a-z]/.test(name)) offences.push(`${relative(SRC, file)} imports ${name}() from client module ${m[2]}`);
        }
      }
    }
    expect(offences, offences.join("\n")).toEqual([]);
  });
});
