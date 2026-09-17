import { describe, expect, it } from "vitest";
import { quoteLink } from "@/lib/quoteLink";

describe("quoteLink — the citation opens the article on the quote", () => {
  it("sends a short quote whole", () => {
    expect(quoteLink("https://h.example/a", "We will not roll back the fee")).toBe("https://h.example/a#:~:text=We%20will%20not%20roll%20back%20the%20fee");
  });
  it("sends a long quote as its first and last six words", () => {
    const q = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen";
    expect(quoteLink("https://h.example/a?x=1", q)).toBe("https://h.example/a?x=1#:~:text=one%20two%20three%20four%20five%20six,nine%20ten%20eleven%20twelve%20thirteen%20fourteen");
  });
  it("escapes the fragment's own delimiters", () => {
    expect(quoteLink("https://h.example/a", "fee, not a tax - he said")).toContain("fee%2C%20not%20a%20tax%20%2D%20he%20said");
  });
});
