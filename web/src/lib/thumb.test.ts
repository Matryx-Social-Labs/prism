import { describe, expect, it } from "vitest";
import { CARD_W, THUMB_W, thumbUrl } from "@/lib/thumb";

// Byte counts in these tests are real — each rule was verified by fetching both
// URLs before it was written. See lib/thumb.ts for the numbers.
describe("publisher CDN thumbnails", () => {
  it("swaps The Hindu's size variant, and only to one that exists", () => {
    const src =
      "https://th-i.thgim.com/public/incoming/gsl0mr/article71254334.ece/alternates/LANDSCAPE_1200/x.jpg";
    // 167,535B → 33,960B
    expect(thumbUrl(src, CARD_W)).toContain("/alternates/FREE_435/");
    // 167,535B → 3,134B for a genuinely tiny box
    expect(thumbUrl(src, THUMB_W <= 96 ? THUMB_W : 64)).toContain("/alternates/SQUARE_80/");
    // The variant set is fixed — never invent one from the requested width.
    expect(thumbUrl(src, 275)).not.toMatch(/alternates\/\w*275/);
  });

  it("rewrites Times of India to a width-parameterised thumb", () => {
    const src = "https://static.toiimg.com/photo/msid-132606785,imgsize-167905.cms";
    // 144,311B → 4,944B
    expect(thumbUrl(src, 200)).toBe(
      "https://static.toiimg.com/thumb/msid-132606785,width-200,resizemode-4.cms",
    );
  });

  it("shrinks the Blogger size segment — the worst offender at 455KB", () => {
    const src = "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEi/s1600/chatgpt.jpg";
    expect(thumbUrl(src, 200)).toContain("/s200/"); // 455,550B → 8,472B
    expect(thumbUrl(src, 200)).not.toContain("/s1600/");
  });

  it("adds a 16:9 size query for India Today", () => {
    const src = "https://akm-img-a-in.tosshub.com/aajtak/images/story/202607/x-16x9.png";
    expect(thumbUrl(src, 352)).toContain("size=352%3A198");
  });

  // A wrong guess is a broken image in the feed, so anything unproven is left be.
  it("passes through hosts with no verified rule", () => {
    for (const src of [
      // Both bake one fixed size into the path and 404 on every other size tried.
      "https://www.hindustantimes.com/ht-img/img/2026/07/24/1600x900/logo/a_123.jpg",
      "https://www.livemint.com/lm-img/img/2026/07/24/1600x900/logo/b_456.jpg",
      "https://www.bleepstatic.com/content/hl-images/2026/07/22/sign.jpg",
    ]) {
      expect(thumbUrl(src, 200)).toBe(src);
    }
  });

  it("leaves a malformed or relative src alone instead of throwing", () => {
    expect(thumbUrl("/og/fallback.png", 200)).toBe("/og/fallback.png");
    expect(thumbUrl("", 200)).toBe("");
  });

  it("does not touch a Hindu URL that has no alternates segment", () => {
    const src = "https://www.thehindu.com/theme/images/og-image.png";
    expect(thumbUrl(src, 200)).toBe(src);
  });
});
