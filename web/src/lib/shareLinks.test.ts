import { describe, expect, it } from "vitest";

import { type Facts, X_LIMIT, body, cardImages, draft, kindOf, shareUrl, targetPath, xLength } from "@/lib/shareLinks";

const LINK = "https://readprism.news/go/k3f9qa";
const STORY: Facts = { kind: "story", title: "Boeing 737 MAX software glitch affects navigation during landing", outlets: 9, monitored: 41 };
const ALL: Facts[] = [
  STORY,
  { kind: "story", title: "A one-outlet report", outlets: 1, monitored: 41 },
  { kind: "quote", speaker: "Nirmala Sitharaman", story: "UPI charges" },
  { kind: "trending", title: "The UPI charges debate" },
  { kind: "entity", name: "Nirmala Sitharaman", records: 75, quotes: 42 },
  { kind: "entity", name: "A new name", records: 1, quotes: 0 },
  { kind: "state", name: "Karnataka", multi: 327, days: 30 },
  { kind: "day", long: "27 September 2026", multi: 315 },
  { kind: "day", long: "2 September 2026", multi: null },
  { kind: "page", name: "The front page (landing)", path: "/" },
  { kind: "page", name: "Prism Plus", path: "/plus" },
];

describe("what a pasted address opens", () => {
  it("is the path of a public Prism page, however it was pasted", () => {
    expect(targetPath("https://www.readprism.news/story/abc?utm_source=x#said")).toBe("/story/abc");
    expect(targetPath("readprism.news/state/kerala/")).toBe("/state/kerala");
    expect(targetPath("/feed/2026-09-27")).toBe("/feed/2026-09-27");
    expect(targetPath("http://localhost:3007/entity/x", "localhost:3007")).toBe("/entity/x");
    expect(targetPath("https://readprism.news")).toBe("/");
  });

  it("is null for another site, a private page, or not an address", () => {
    for (const bad of ["https://evil.example/story/x", "//evil.example/story/x", "/admin", "/account", "/signin", "javascript:alert(1)", "readprism.news.evil.example/story/x", "not a link",
      "/story/../admin", "/story/%2e%2e/admin", "/plus/welcome"]) {
      expect(targetPath(bad)).toBeNull();
    }
  });

  it("names the kind of page", () => {
    expect([kindOf("/story/a/quote/q1"), kindOf("/story/a"), kindOf("/feed/2026-09-27"), kindOf("/feed"), kindOf("/"), kindOf("/state/kerala")]).toEqual(
      ["quote", "story", "day", "feed", "landing", "state"],
    );
  });
});

describe("the post", () => {
  it("prints only the page's own counts, as the page prints them", () => {
    expect(body(STORY)).toBe("Boeing 737 MAX software glitch affects navigation during landing\n\nReported by 9 of 41 monitored outlets: every report, and who said what, on one page.");
    expect(body(ALL[1])).toContain("Reported by 1 of 41 monitored outlets so far");
    expect(body(ALL[4])).toBe("Nirmala Sitharaman: every Prism record that names them, and 42 quotes checked word for word against the article.");
    expect(body(ALL[5])).toBe("A new name: every Prism record that names them.");
    expect(body(ALL[8])).toBe("The record for 2 September 2026.");
  });

  it("never says what the product must not (CLAUDE.md, PRODUCT.md), and never names a lens", () => {
    for (const f of ALL) {
      const text = body(f);
      expect(text).not.toMatch(/AI-powered|\bAI\b|unbiased|\bmodel\b|Markets|Cyber|Health|Policy|breaking|exclusive/i);
    }
  });

  it("fits X with its link, and leaves the link off an Instagram caption", () => {
    const long: Facts = { ...STORY, title: "A ".repeat(200).trim() };
    expect(xLength(draft(long, "x", LINK))).toBeLessThanOrEqual(X_LIMIT);
    expect(draft(STORY, "x", LINK)).not.toContain(LINK); // the intent adds it
    expect(draft(STORY, "instagram", LINK)).not.toContain(LINK);
    expect(draft(STORY, "whatsapp", LINK).endsWith(`\n\n${LINK}`)).toBe(true);
  });
});

describe("the button that opens the platform", () => {
  it("carries the post and the link where the platform takes them", () => {
    const post = draft(STORY, "whatsapp", LINK);
    expect(shareUrl("whatsapp", LINK, post, STORY.kind)).toBe(`https://wa.me/?text=${encodeURIComponent(post)}`);
    const x = new URL(shareUrl("x", LINK, "Hello", "t")!);
    expect([x.hostname, x.searchParams.get("text"), x.searchParams.get("url")]).toEqual(["x.com", "Hello", LINK]);
    const tg = new URL(shareUrl("telegram", LINK, `Hi\n\n${LINK}`, "t")!);
    expect([tg.searchParams.get("url"), tg.searchParams.get("text")]).toEqual([LINK, "Hi"]);
    expect(new URL(shareUrl("linkedin", LINK, "x", "t")!).searchParams.get("url")).toBe(LINK);
  });

  it("is none for a platform with no share address (Instagram, launch sites): copy the post instead", () => {
    for (const p of ["instagram", "producthunt", "hn", "newsletter", "press"] as const) expect(shareUrl(p, LINK, "x", "t")).toBeNull();
  });
});

describe("a page's share images", () => {
  it("are the page's own card where it has one, the brand card where it does not", () => {
    expect(cardImages("/story/abc")).toEqual({ preview: "/story/abc/opengraph-image", portrait: "/card/portrait/story/abc", story: "/card/story/story/abc" });
    expect(cardImages("/story/abc/quote/q1").preview).toBe("/story/abc/quote/q1/opengraph-image");
    expect(cardImages("/feed/2026-09-27").preview).toBe("/feed/2026-09-27/opengraph-image");
    expect(cardImages("/")).toEqual({ preview: "/opengraph-image", portrait: "/card/portrait/site", story: "/card/story/site" });
    expect(cardImages("/plus").preview).toBe("/opengraph-image");
    expect(cardImages("/feed").preview).toBe("/opengraph-image");
  });
});
