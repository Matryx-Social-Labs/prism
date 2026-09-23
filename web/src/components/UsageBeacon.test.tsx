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

  it("never counts the founders reading /admin", () => {
    pathname.current = "/admin/labellers";
    render(<UsageBeacon />);
    expect(send).not.toHaveBeenCalled();
  });
});
