import { afterEach, describe, expect, it } from "vitest";
import { afterSignIn, rememberNext, safeNext, takeNext } from "@/lib/next";

describe("next", () => {
  afterEach(() => window.sessionStorage.clear());

  it("honours only a same-site path — never a URL or a protocol-relative one", () => {
    expect(safeNext("/plus?from=ask-limit")).toBe("/plus?from=ask-limit");
    expect(safeNext("https://evil.example/")).toBeNull();
    expect(safeNext("//evil.example")).toBeNull();
    // A browser reads "/\\host" as protocol-relative too.
    expect(safeNext("/\\evil.example")).toBeNull();
    expect(safeNext("")).toBeNull();
  });

  // Review 2026-09-29: a URL parser strips tab, CR and LF anywhere, so
  // "/\t/evil.example" resolves to https://evil.example after sign-in.
  it("refuses a path a browser would turn into another host", () => {
    for (const hop of ["/\t/evil.example", "/\n/evil.example", "/\r/evil.example", "/\t\\evil.example"]) {
      expect(new URL(hop, "https://www.readprism.news").origin).not.toBe("https://www.readprism.news");
      expect(safeNext(hop)).toBeNull();
    }
    expect(safeNext("/story/abc?next=%2Ffeed")).toBe("/story/abc?next=%2Ffeed");
  });

  it("prefers the query, then what this tab remembered, then the chart — and forgets after one read", () => {
    rememberNext("/story/abc");
    expect(takeNext("/feed", "/plus")).toBe("/plus");
    rememberNext("/story/abc");
    expect(takeNext()).toBe("/story/abc");
    expect(takeNext()).toBe("/feed");
  });

  it("routes a new reader through onboarding and keeps the destination", () => {
    expect(afterSignIn(true, "/feed")).toBe("/onboarding?next=%2Ffeed");
    expect(afterSignIn(false, "/feed")).toBe("/feed");
  });

  // Audit 2026-09-29 (P1-8): a reader who signed up at a lens or Ask gate came
  // for that story, or to pay; onboarding must not stand between them and it.
  it("sends a new reader straight back to a story or to /plus", () => {
    expect(afterSignIn(true, "/story/e1")).toBe("/story/e1");
    expect(afterSignIn(true, "/plus")).toBe("/plus");
    expect(afterSignIn(true, "/plus?from=lens-limit&next=%2Fstory%2Fe1")).toBe("/plus?from=lens-limit&next=%2Fstory%2Fe1");
    expect(afterSignIn(true, "/plusses")).toBe("/onboarding?next=%2Fplusses");
    expect(afterSignIn(true, "/storyline")).toBe("/onboarding?next=%2Fstoryline");
  });
});
