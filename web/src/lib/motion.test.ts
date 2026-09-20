import { describe, expect, it } from "vitest";
import { flipDuration } from "@/lib/motion";

describe("the flip's clock", () => {
  // REGRESSION: the scan line ran 500ms whatever the block's height, so a
  // five-point brief was swept three times faster than the locked Markets box
  // and the re-ink read as a jump. The pace is constant; the clock is the height.
  it("holds a constant pace between a short box and a long brief", () => {
    expect(flipDuration(300)).toBe(500); // floor: a three-line locked box
    expect(flipDuration(720)).toBe(800); // 0.9px per ms
    expect(flipDuration(2000)).toBe(1100); // ceiling: never a slow crawl
  });
});
