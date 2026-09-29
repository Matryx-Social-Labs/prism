import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";

import { UsageBeacon } from "@/components/UsageBeacon";

const send = vi.hoisted(() => vi.fn());
const pathname = vi.hoisted(() => ({ current: "/story/7f9d86ff" }));

vi.mock("@/lib/analytics", async (orig) => ({ ...(await orig<typeof import("@/lib/analytics")>()), send }));
vi.mock("next/navigation", () => ({ usePathname: () => pathname.current }));

beforeEach(() => {
  send.mockReset();
  sessionStorage.clear();
  pathname.current = "/story/7f9d86ff";
});
afterEach(() => vi.unstubAllGlobals());

describe("the usage beacon", () => {
  it("counts the kind of page, never the story", () => {
    render(<UsageBeacon />);
    expect(send).toHaveBeenCalledWith("view", "story");
    expect(JSON.stringify(send.mock.calls)).not.toContain("7f9d86ff");
  });

  it("counts an arrival once per tab, with the referrer's host and nothing else", () => {
    Object.defineProperty(document, "referrer", { value: "https://www.google.co.in/search?q=private+words", configurable: true });
    const { rerender } = render(<UsageBeacon />);
    pathname.current = "/feed";
    rerender(<UsageBeacon />);
    const arrivals = send.mock.calls.filter(([e]) => e === "arrival");
    expect(arrivals).toEqual([["arrival", "", { ref: "www.google.co.in", s: "" }]]);
    expect(JSON.stringify(send.mock.calls)).not.toContain("private");
  });

  // Audit 2026-09-29 §2.5: does a visit go past one story? The 2nd and 5th, per tab.
  it("counts the second and fifth story read in a tab, and no other", () => {
    const depth = () => send.mock.calls.filter(([e]) => e === "depth");
    const { rerender } = render(<UsageBeacon />);
    pathname.current = "/feed";
    rerender(<UsageBeacon />);
    expect(depth()).toEqual([]); // a page that is not a story is not a story read
    for (const path of ["/story/b", "/story/c", "/story/d", "/story/e", "/story/f"]) {
      pathname.current = path;
      rerender(<UsageBeacon />);
    }
    expect(depth()).toEqual([["depth", "2"], ["depth", "5"]]);
  });

  it("counts a click on a marked button by its word, and nothing else", async () => {
    render(<UsageBeacon />);
    document.body.insertAdjacentHTML("beforeend", '<a href="#" data-cta="landing:hero"><span>Read</span></a><a href="#">Other</a>');
    document.querySelector("[data-cta] span")!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    (document.body.lastElementChild as HTMLElement).click();
    expect(send.mock.calls.filter(([e]) => e === "cta")).toEqual([["cta", "landing:hero"]]);
    document.body.innerHTML = "";
  });

  it("never counts the founders reading /admin", () => {
    pathname.current = "/admin/labellers";
    render(<UsageBeacon />);
    expect(send).not.toHaveBeenCalled();
  });
});
