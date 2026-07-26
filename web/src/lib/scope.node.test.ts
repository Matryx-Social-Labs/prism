// @vitest-environment node
//
// The SSR half of scope.ts. jsdom always defines `window`, so under the normal
// environment both `typeof window === "undefined"` guards are unreachable and
// the suite was proving nothing about the server render — where Next runs this
// module first, before any browser exists.
import { describe, expect, it } from "vitest";
import { loadScope, saveScope } from "@/lib/scope";

describe("scope on the server", () => {
  it("has no window, so this file is testing what it claims to", () => {
    expect(typeof window).toBe("undefined");
  });

  it("reads as unchosen so the caller keeps its own default", () => {
    expect(loadScope()).toBeNull();
    expect(loadScope(false)).toBeNull();
  });

  // A throw here is a 500 on the server render, not a degraded preference.
  it("swallows a write instead of crashing the render", () => {
    expect(() => saveScope("world")).not.toThrow();
  });
});
