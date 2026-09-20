import { afterEach, describe, expect, it } from "vitest";
import { cameFromInside, notePath } from "@/lib/nav";

describe("nav memory", () => {
  afterEach(() => window.sessionStorage.clear());

  it("a first load has no previous path: not from inside", () => {
    notePath("/story/abc");
    expect(cameFromInside()).toBe(false);
  });

  it("a second client navigation remembers where it came from", () => {
    notePath("/feed");
    notePath("/story/abc");
    Object.defineProperty(window.history, "length", { value: 2, configurable: true });
    expect(cameFromInside()).toBe(true);
  });

  it("re-noting the same path (a re-render) changes nothing", () => {
    notePath("/story/abc");
    notePath("/story/abc");
    expect(cameFromInside()).toBe(false);
  });
});
