import { describe, expect, it } from "vitest";
import { LENS_META, LENS_ORDER, lensMeta } from "@/lib/lenses";

describe("lensMeta", () => {
  it("returns the registry entry for a known lens", () => {
    expect(lensMeta("markets").short).toBe("Markets");
    expect(lensMeta("cyber").short).toBe("Cyber");
  });

  // The lens set grows on the backend; the client must not crash on one it
  // hasn't shipped styling for yet.
  it("falls back to the reader lens for an unknown slug", () => {
    expect(lensMeta("quant-2027").slug).toBe("reader");
  });

  it("gives every shipped lens a plain-language description", () => {
    // Prose uses `plain` so a reader outside that profession understands the
    // offer; the role name ("Cybersecurity / GRC") is picker-only.
    for (const slug of LENS_ORDER) {
      const m = LENS_META[slug];
      expect(m.plain, `${slug} is missing plain`).toBeTruthy();
      expect(m.plain).not.toMatch(/\//); // no slashed role jargon in prose
    }
  });

  it("keeps the role name and the plain description distinct", () => {
    // Regression: prose used to print `name`, which reads as jargon.
    expect(LENS_META.cyber.name).toBe("Cybersecurity / GRC");
    expect(LENS_META.cyber.plain).not.toBe(LENS_META.cyber.name);
    expect(LENS_META.markets.name).toBe("Finance / Trader");
    expect(LENS_META.markets.plain).not.toBe(LENS_META.markets.name);
  });

  it("gives each lens a distinct hue, so color identifies who is speaking", () => {
    const colors = LENS_ORDER.map((s) => LENS_META[s].color);
    expect(new Set(colors).size).toBe(colors.length);
  });
});
