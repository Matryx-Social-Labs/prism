import { describe, expect, it } from "vitest";
import { bodyStack, displayStack, indicFamilyFor } from "@/lib/ogFonts";

describe("script detection for social cards", () => {
  it.each([
    ["उत्तर प्रदेश पुलिस में निकली भर्तियां", "Noto Serif Devanagari"],
    ["தமிழ்நாடு அரசு அறிவிப்பு", "Noto Serif Tamil"],
    ["ఆంధ్రప్రదేశ్ ప్రభుత్వం", "Noto Serif Telugu"],
    ["পশ্চিমবঙ্গ সরকার", "Noto Serif Bengali"],
    ["ગુજરાત સરકાર", "Noto Serif Gujarati"],
    ["ಕರ್ನಾಟಕ ಸರ್ಕಾರ", "Noto Serif Kannada"],
    ["കേരള സർക്കാർ", "Noto Serif Malayalam"],
    ["ਪੰਜਾਬ ਸਰਕਾਰ", "Noto Serif Gurmukhi"],
    ["ଓଡ଼ିଶା ସରକାର", "Noto Serif Oriya"],
  ])("picks a family for %s", (text, family) => {
    expect(indicFamilyFor(text)).toBe(family);
  });

  it("asks for no extra family when the headline is Latin", () => {
    expect(indicFamilyFor("Delhi Police · Sonam Wangchuk")).toBeNull();
    expect(displayStack("Delhi Police")).toBe("Newsreader, Georgia, serif");
  });

  // The Indic face has to win for its own glyphs, so it goes first — Newsreader
  // has no Devanagari and would otherwise claim the run. The record voice is the
  // script's Noto Serif; the reading voice is its Anek (tokens/typography.css).
  it("puts the Indic family ahead of the record voice in the stack", () => {
    expect(displayStack("उत्तर प्रदेश")).toBe("Noto Serif Devanagari, Newsreader, Georgia, serif");
    expect(bodyStack("ಕರ್ನಾಟಕ ಸರ್ಕಾರ")).toBe("Anek Kannada, Anek Latin, sans-serif");
    expect(bodyStack("Noel Tata")).toBe("Anek Latin, sans-serif");
  });

  // A headline that mixes scripts still needs the non-Latin one covered.
  it("handles a headline that mixes Latin and Indic", () => {
    expect(indicFamilyFor("UP Police: 81,000 पदों पर भर्ती")).toBe("Noto Serif Devanagari");
  });

  it("ignores digits and punctuation, which every family covers", () => {
    expect(indicFamilyFor("81,000 · 2026 — (updated)")).toBeNull();
  });
});
