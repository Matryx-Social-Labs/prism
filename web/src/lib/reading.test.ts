import { describe, expect, it } from "vitest";
import { confidenceWords } from "@/lib/reading";

describe("A model's confidence is printed in words, never as its number", () => {
  it.each([
    [0, "low confidence"],
    [0.49, "low confidence"],
    [0.5, "moderate confidence"],
    [0.74, "moderate confidence"],
    [0.75, "high confidence"],
    [1, "high confidence"],
  ])("%s → %s", (c, words) => {
    expect(confidenceWords(c)).toBe(words);
  });
});
