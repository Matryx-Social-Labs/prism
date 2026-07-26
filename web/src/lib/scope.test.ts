import { afterEach, describe, expect, it, vi } from "vitest";
import { loadScope, saveScope } from "@/lib/scope";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("scope persistence", () => {
  // REGRESSION: scope lived in a module cache that died on reload, and the feed
  // re-defaulted to "region" on every fresh mount. Picking World and refreshing
  // snapped straight back to your state.
  it("survives a reload", () => {
    saveScope("world");
    expect(loadScope()).toBe("world");
  });

  it("returns null when the reader has never chosen, so the caller can default", () => {
    expect(loadScope()).toBeNull();
  });

  it("ignores a corrupt value rather than trusting it", () => {
    localStorage.setItem("parse.scope.v1", "everywhere");
    expect(loadScope()).toBeNull();
  });

  it.each(["all", "region", "world"] as const)("round-trips %s", (s) => {
    saveScope(s);
    expect(loadScope()).toBe(s);
  });

  // Blocked storage is the WhatsApp/Instagram in-app browser case.
  it("degrades quietly when storage is blocked", () => {
    const boom = () => {
      throw new DOMException("denied", "SecurityError");
    };
    vi.stubGlobal("localStorage", { getItem: boom, setItem: boom });
    expect(() => saveScope("world")).not.toThrow();
    expect(loadScope()).toBeNull();
  });
});
