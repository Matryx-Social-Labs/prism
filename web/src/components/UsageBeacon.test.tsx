import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";

import { UsageBeacon } from "@/components/UsageBeacon";

const send = vi.hoisted(() => vi.fn());
const pathname = vi.hoisted(() => ({ current: "/story/7f9d86ff" }));

vi.mock("@/lib/analytics", async (orig) => ({ ...(await orig<typeof import("@/lib/analytics")>()), send }));
vi.mock("next/navigation", () => ({ usePathname: () => pathname.current }));

beforeEach(() => {
  send.mockReset();
  sessionStorage.clear();
  pathname.current = "/story/7f9d86ff";
  window.history.replaceState(null, "", "/story/7f9d86ff");
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

  // Founder links (/admin/marketing): the code in utm_content, then what the visit did next.
  it("counts a founder link's code once, then a 2nd story and the Plus page once each against it", () => {
    window.history.replaceState(null, "", "/story/7f9d86ff?utm_source=x&utm_medium=social&utm_content=K3F9QA");
    const { rerender } = render(<UsageBeacon />);
    expect(window.location.search).toBe("");
    for (const path of ["/story/b", "/plus", "/feed", "/plus", "/story/c"]) {
      pathname.current = path;
      rerender(<UsageBeacon />);
    }
    expect(send.mock.calls.filter(([e]) => e === "link" || e === "goal")).toEqual([
      ["link", "k3f9qa"], ["goal", "k3f9qa:read2"], ["goal", "k3f9qa:plus"],
    ]);
  });

  it("counts nothing against a link when the visit came by none, or by a utm_content that is not a code", () => {
    window.history.replaceState(null, "", "/story/7f9d86ff?utm_source=x&utm_content=hero_cta");
    const { rerender } = render(<UsageBeacon />);
    for (const path of ["/story/b", "/plus"]) {
      pathname.current = path;
      rerender(<UsageBeacon />);
    }
    expect(send.mock.calls.filter(([e]) => e === "link" || e === "goal")).toEqual([]);
  });

  it("never counts the founders reading /admin", () => {
    pathname.current = "/admin/labellers";
    render(<UsageBeacon />);
    expect(send).not.toHaveBeenCalled();
  });

  // Launch attribution, 06 §2.3: the campaign word a link carried, once a visit.
  it("counts the campaign word once per visit, from a closed list, and takes it out of the address", () => {
    window.history.replaceState(null, "", "/story/7f9d86ff?s=story&ref=ProductHunt&utm_medium=launch#said");
    const { rerender } = render(<UsageBeacon />);
    // The share marker stays (it is how the arrival was counted); the campaign words go.
    expect(window.location.pathname + window.location.search + window.location.hash).toBe("/story/7f9d86ff?s=story#said");
    // A second campaign link opened in the same visit is not a second arrival, but still leaves the address.
    window.history.replaceState(null, "", "/feed?ref=hn");
    pathname.current = "/feed";
    rerender(<UsageBeacon />);
    expect(send.mock.calls.filter(([e]) => e === "campaign")).toEqual([["campaign", "producthunt"]]);
    expect(window.location.search).toBe("");
  });

  it("counts a word not on the list as other, and reads utm_source when there is no ref", () => {
    window.history.replaceState(null, "", "/?ref=my-blog");
    render(<UsageBeacon />);
    expect(send).toHaveBeenCalledWith("campaign", "other");
    cleanup();
    sessionStorage.clear();
    send.mockReset();
    window.history.replaceState(null, "", "/?utm_source=twitter&utm_campaign=launch");
    render(<UsageBeacon />);
    expect(send.mock.calls.filter(([e]) => e === "campaign")).toEqual([["campaign", "x"]]);
    expect(window.location.search).toBe("");
  });

  it("counts no campaign for a link that carried none", () => {
    render(<UsageBeacon />);
    expect(send.mock.calls.filter(([e]) => e === "campaign")).toEqual([]);
  });

  // The share loop, 06 §2.2b: does a visit a shared link brought go on to a 2nd story?
  it("counts the 2nd story of a visit that arrived by a shared link as 2:share, and only that visit", () => {
    const read = (first: string) => {
      window.history.replaceState(null, "", first);
      pathname.current = "/story/a";
      const { rerender, unmount } = render(<UsageBeacon />);
      pathname.current = "/story/b";
      rerender(<UsageBeacon />);
      unmount();
      const depth = send.mock.calls.filter(([e]) => e === "depth");
      send.mockReset();
      sessionStorage.clear();
      return depth;
    };
    expect(read("/story/a?s=story")).toEqual([["depth", "2"], ["depth", "2:share"]]);
    expect(read("/story/a")).toEqual([["depth", "2"]]);
    expect(read("/story/a?s=made-up")).toEqual([["depth", "2"]]);
  });
});
