import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SiteCard, StoryCard, quoteCheckLine, tally } from "@/lib/ogCard";

describe("the quote card's check line", () => {
  // Moved from quotes.test.ts with the v3 card: the card is shared alone, so the
  // words "word for word" must never sit over an outlet's own translation.
  it("never says word for word over an outlet's translation", () => {
    expect(quoteCheckLine(true)).toBe("Checked against the article · the outlet translated these words");
    expect(quoteCheckLine(true)).not.toMatch(/word for word/i);
    expect(quoteCheckLine(false)).toBe("Word for word, checked against the article");
  });

  it("says reported words are the article's report of what was said, never word for word", () => {
    expect(quoteCheckLine(false, true)).toBe("Checked against the article · its report of what was said, not a quote");
    expect(quoteCheckLine(false, true)).not.toMatch(/word for word/i);
  });
});

describe("the card's coverage tally", () => {
  it("counts a masthead once, so the legend adds up to the outlet count", () => {
    const t = tally([
      { publisher: "The Hindu", origin: "national", language: "en" },
      { publisher: "The Hindu", origin: "national", language: "en" },
      { publisher: "Prajavani", origin: "regional", language: "kn" },
      { publisher: "Reuters", origin: "wire", language: "en" },
    ]);
    expect(t.outlets).toBe(3);
    expect(t.counts).toEqual({ national: 1, intl: 0, regional: 1, wire: 1 });
    expect(Object.values(t.counts).reduce((a, b) => a + b, 0)).toBe(t.outlets);
    expect(t.languages).toEqual(["en", "kn"]); // most reports first
  });

  it("reads a report with no language as English and one with no origin as uncounted", () => {
    const t = tally([{ publisher: "Mint", origin: null, language: null }]);
    expect(t).toEqual({ counts: { national: 0, intl: 0, regional: 0, wire: 0 }, outlets: 1, languages: ["en"] });
  });
});

describe("the card's frame", () => {
  // The lockup is readPrism.news, so the mono line beside it prints only the path
  // (screens/Wordmark.html); the site card has no path, so it prints none.
  const head = (c: HTMLElement) => c.firstElementChild!.firstElementChild!.textContent;

  it("prints the path beside the lockup, and nothing on the site card", () => {
    const story = render(<StoryCard path="/story/e1" meta={[]} headline="A story" tally={tally([])} count="0 outlets" />);
    expect(head(story.container)).toBe("readPrism.news/story/e1");
    const site = render(<SiteCard headline="Follow the story" line="One record" />);
    expect(head(site.container)).toBe("readPrism.news");
  });
});
