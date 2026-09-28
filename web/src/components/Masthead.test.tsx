import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Masthead } from "@/components/Masthead";

vi.mock("@/components/ThemeToggle", () => ({ ThemeToggle: () => null }));

/**
 * The full lockup is wider than the old "Prism", so the phone dateline steps down
 * by the masthead's width instead of clipping to "MON 28 SE…" (screens/Wordmark.html,
 * spec · Phone dateline). globals.css picks the rung; this pins what each rung holds.
 */
describe("Masthead dateline ladder", () => {
  const rungs = (c: HTMLElement) => ["l", "m", "s"].map((k) => c.querySelector(`.p-dateline__${k}`)?.textContent);

  it("prints each rung it is given", () => {
    const { container } = render(<Masthead dateline="Mon, 28 Sep" datelineM="28 Sep" datelineS="28" />);
    expect(rungs(container)).toEqual(["Mon, 28 Sep", "28 Sep", "28"]);
  });

  it("falls back to the next longer rung when a short one is not given", () => {
    const { container } = render(<Masthead dateline="Search" />);
    expect(rungs(container)).toEqual(["Search", "Search", "Search"]);
    const { container: c2 } = render(<Masthead dateline="Stories · 14:32 IST" datelineM="14:32 IST" />);
    expect(rungs(c2)).toEqual(["Stories · 14:32 IST", "14:32 IST", "14:32 IST"]);
  });
});
