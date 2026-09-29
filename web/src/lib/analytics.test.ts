import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { pageKind, send, shareSurface, track, word } from "@/lib/analytics";

const fetchSpy = vi.hoisted(() => vi.fn());
// A signed-in reader whose session is the HttpOnly cookie: the page holds no token.
vi.mock("@/lib/session", () => ({ loadSession: () => ({ userId: "u", email: "e@example.test" }), authHeader: () => ({}) }));

beforeEach(() => {
  localStorage.clear();
  fetchSpy.mockReset().mockResolvedValue(new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetchSpy);
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

const sent = () => JSON.parse(fetchSpy.mock.calls[0][1].body as string);

describe("usage counting", () => {
  it("never reaches the network under the test runner", () => {
    track("Ask", { via: "bar" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("posts one event and one word, with the session cookie so the day can be noted", () => {
    vi.stubEnv("NODE_ENV", "production");
    track("Lens", { lens: "markets", locked: true });
    expect(sent()).toEqual({ e: "lens", d: "markets:locked" });
    expect(fetchSpy.mock.calls[0][1].credentials).toBe("include");
    expect(fetchSpy.mock.calls[0][1].keepalive).toBe(true);
  });

  it("sends the session on the first beacon of the day only; every other count omits it", () => {
    vi.stubEnv("NODE_ENV", "production");
    send("view", "feed");
    send("view", "story");
    track("Ask", { via: "bar" });
    const modes = fetchSpy.mock.calls.map(([, init]) => (init as RequestInit).credentials);
    expect(modes).toEqual(["include", "omit", "omit"]);
  });

  it("keeps the step of subscribing and what led there, as a slug", () => {
    vi.stubEnv("NODE_ENV", "production");
    track("Subscribe", { stage: "prompt", from: "Ask limit" });
    expect(sent().d).toBe("prompt:ask-limit");
  });

  // Audit 2026-09-29 §2.5: each word is one the API keeps (common/usage.py).
  it("words the funnel before paying as the API's closed lists", () => {
    vi.stubEnv("NODE_ENV", "production");
    track("Sign in", { stage: "sent", method: "link" });
    track("Sign in", { method: "google" });
    track("Onboarding", { stage: "step", step: 2 });
    track("Onboarding", { stage: "done", saved: "account" });
    track("Tab", { tab: "foryou" });
    track("Subscribe", { stage: "declined", plan: "plus_monthly" });
    const words = fetchSpy.mock.calls.map(([, init]) => JSON.parse((init as RequestInit).body as string));
    expect(words).toEqual([
      { e: "signin", d: "sent:link" },
      { e: "signin", d: "google" },
      { e: "onboarding", d: "step:2" },
      { e: "onboarding", d: "done:account" },
      { e: "tab", d: "foryou" },
      { e: "subscribe", d: "declined:plus_monthly" },
    ]);
  });

  it("swallows a failed count", async () => {
    vi.stubEnv("NODE_ENV", "production");
    fetchSpy.mockRejectedValue(new Error("offline"));
    expect(() => send("view", "feed")).not.toThrow();
  });

  it("reduces a path to a kind of page, never an id", () => {
    expect(pageKind("/")).toBe("landing");
    expect(pageKind("/story/7f9d86ff")).toBe("story");
    expect(pageKind("/story/7f9d86ff/quote/0-1")).toBe("quote");
    expect(pageKind("/trending/rbi-rate-cut")).toBe("trending");
    expect(pageKind("/you")).toBe("account");
    expect(pageKind("/privacy")).toBe("legal");
    expect(pageKind("/wp-admin")).toBe("other");
    expect(shareSurface("https://www.readprism.news/story/x/quote/1")).toBe("quote");
    expect(word("A Very Long Stage Name With Spaces", "and/slashes")).toBe("a-very-long-stage-name-with-spaces:and-slashes");
  });
});
