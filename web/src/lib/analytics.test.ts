import { afterEach, describe, expect, it, vi } from "vitest";
import { track } from "@/lib/analytics";

describe("track", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("is a no-op when the script is not loaded", () => {
    expect(() => track("Ask")).not.toThrow();
  });

  it("forwards the event and props to Plausible when it is", () => {
    const plausible = vi.fn();
    vi.stubGlobal("plausible", plausible);
    track("Lens", { lens: "markets", locked: true });
    expect(plausible).toHaveBeenCalledWith("Lens", { props: { lens: "markets", locked: true } });
  });
});
