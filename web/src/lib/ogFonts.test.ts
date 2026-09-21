import { describe, expect, it } from "vitest";
import { displayStack, indicFamilyFor } from "@/lib/ogFonts";

describe("script detection for social cards", () => {
  it.each([
    ["उत्तर प्रदेश पुलिस में निकली भर्तियां", "Noto Sans Devanagari"],
    ["தமிழ்நாடு அரசு அறிவிப்பு", "Noto Sans Tamil"],
    ["ఆంధ్రప్రదేశ్ ప్రభుత్వం", "Noto Sans Telugu"],
    ["পশ্চিমবঙ্গ সরকার", "Noto Sans Bengali"],
    ["ગુજરાત સરકાર", "Noto Sans Gujarati"],
    ["ಕರ್ನಾಟಕ ಸರ್ಕಾರ", "Noto Sans Kannada"],
    ["കേരള സർക്കാർ", "Noto Sans Malayalam"],
  ])("picks a family for %s", (text, family) => {
    expect(indicFamilyFor(text)).toBe(family);
  });

  it("asks for no extra family when the headline is Latin", () => {
    expect(indicFamilyFor("Delhi Police · Sonam Wangchuk")).toBeNull();
    expect(displayStack("Delhi Police")).toBe("Libre Baskerville, Georgia, serif");
  });

  // The Indic face has to win for its own glyphs, so it goes first — Fraunces
  // has no Devanagari and would otherwise claim the run.
  it("puts the Indic family ahead of the record voice in the stack", () => {
    expect(displayStack("उत्तर प्रदेश")).toBe("Noto Sans Devanagari, Libre Baskerville, Georgia, serif");
  });

  // A headline that mixes scripts still needs the non-Latin one covered.
  it("handles a headline that mixes Latin and Indic", () => {
    expect(indicFamilyFor("UP Police: 81,000 पदों पर भर्ती")).toBe("Noto Sans Devanagari");
  });

  it("ignores digits and punctuation, which every family covers", () => {
    expect(indicFamilyFor("81,000 · 2026 — (updated)")).toBeNull();
  });
});
