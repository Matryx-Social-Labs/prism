import { describe, expect, it } from "vitest";

import { campaignWord, isShareMarker, linkCode, withoutCampaign } from "@/lib/attribution";
import { PRIVACY } from "@/lib/legal";

const word = (q: string) => campaignWord(new URLSearchParams(q));

describe("the campaign word a link carried", () => {
  it("is one of the closed list, however the link spelt it", () => {
    expect(word("ref=producthunt")).toBe("producthunt");
    expect(word("ref=Product_Hunt")).toBe("producthunt");
    expect(word("utm_source=news.ycombinator.com")).toBe("hn");
    expect(word("utm_source=dev.to")).toBe("devto");
    expect(word("ref=LinkedIn")).toBe("linkedin");
  });

  it("is other for a word not on the list, never the word itself", () => {
    expect(word("ref=someones-blog")).toBe("other");
    expect(word("utm_source=%3Cscript%3E")).toBe("other");
  });

  it("prefers ref to utm_source, and is null when the link carried neither", () => {
    expect(word("ref=hn&utm_source=reddit")).toBe("hn");
    expect(word("ref=&utm_source=reddit")).toBe("reddit");
    expect(word("s=story")).toBeNull();
    expect(word("")).toBeNull();
  });
});

describe("a founder link's code", () => {
  const code = (q: string) => linkCode(new URLSearchParams(q));
  it("is utm_content when it is one of share_links' codes, lowercased", () => {
    expect(code("utm_content=k3f9qa")).toBe("k3f9qa");
    expect(code("utm_content=K3F9QA")).toBe("k3f9qa");
  });
  it("is null for any other utm_content: a word, the wrong length, a letter never used", () => {
    for (const q of ["utm_content=hero_cta", "utm_content=k3f9q", "utm_content=k3f9qa1", "utm_content=k3f0qa", "utm_content=l1io23", ""]) {
      expect(code(q)).toBeNull();
    }
  });
});

describe("the address without its campaign words", () => {
  it("drops ref and every utm_ key, and keeps the rest of the query and the hash", () => {
    expect(withoutCampaign("https://www.readprism.news/story/e1?ref=hn&s=story&utm_source=x&utm_medium=post#said")).toBe("/story/e1?s=story#said");
    expect(withoutCampaign("https://www.readprism.news/?ref=producthunt")).toBe("/");
  });

  it("is null when there is nothing to take out", () => {
    expect(withoutCampaign("https://www.readprism.news/feed?s=story&referrer=x")).toBeNull();
  });
});

describe("the share marker", () => {
  it("is only one of the Share button's surfaces", () => {
    expect(["story", "quote", "trending", "other"].every(isShareMarker)).toBe(true);
    expect(isShareMarker("x")).toBe(false);
    expect(isShareMarker(null)).toBe(false);
  });
});

describe("the privacy policy", () => {
  it("names every new count, and says each is a total from a fixed list", () => {
    const collect = PRIVACY.sections.find((x) => x.heading === "What we collect")!.blocks.flat().join(" ");
    expect(collect).toContain("the campaign word a link to Prism carried");
    expect(collect).toContain("“Where did you hear about Prism?”");
    expect(collect).toContain("“Could you check this story for yourself?”");
    expect(collect).toContain("never words you type");
    // Founder links (/admin/marketing): the code, what it counts, and that it is never kept on an account.
    expect(collect).toContain("A link Prism's founders post carries a short code");
    expect(collect).toContain("the code is not stored with your account");
    const storage = PRIVACY.sections.find((x) => x.heading === "Cookies and device storage")!.blocks.flat().join(" ");
    expect(storage).toContain("kept only until the tab is closed");
  });
});
