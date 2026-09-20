import { afterEach, describe, expect, it } from "vitest";
import { afterSignIn, rememberNext, safeNext, takeNext } from "@/lib/next";

describe("next", () => {
  afterEach(() => window.sessionStorage.clear());

  it("honours only a same-site path — never a URL or a protocol-relative one", () => {
    expect(safeNext("/plus?from=ask-limit")).toBe("/plus?from=ask-limit");
    expect(safeNext("https://evil.example/")).toBeNull();
    expect(safeNext("//evil.example")).toBeNull();
    expect(safeNext("")).toBeNull();
  });

  it("prefers the query, then what this tab remembered, then the chart — and forgets after one read", () => {
    rememberNext("/story/abc");
    expect(takeNext("/feed", "/plus")).toBe("/plus");
    rememberNext("/story/abc");
    expect(takeNext()).toBe("/story/abc");
    expect(takeNext()).toBe("/feed");
  });

  it("routes a new reader through onboarding and keeps the destination", () => {
    expect(afterSignIn(true, "/plus")).toBe("/onboarding?next=%2Fplus");
    expect(afterSignIn(false, "/plus")).toBe("/plus");
  });
});
