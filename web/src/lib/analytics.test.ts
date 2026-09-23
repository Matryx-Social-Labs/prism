import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { pageKind, send, shareSurface, track, word } from "@/lib/analytics";

const fetchSpy = vi.hoisted(() => vi.fn());
vi.mock("@/lib/session", () => ({ loadSession: () => ({ token: "tok", userId: "u", email: "e@example.test" }) }));

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

  it("posts one event and one word, with the session so the day can be noted", () => {
    vi.stubEnv("NODE_ENV", "production");
    track("Lens", { lens: "markets", locked: true });
    expect(sent()).toEqual({ e: "lens", d: "markets:locked" });
    expect(fetchSpy.mock.calls[0][1].headers).toMatchObject({ Authorization: "Bearer tok" });
    expect(fetchSpy.mock.calls[0][1].keepalive).toBe(true);
  });

  it("sends the session on the first beacon of the day only", () => {
    vi.stubEnv("NODE_ENV", "production");
    send("view", "feed");
    send("view", "story");
    track("Ask", { via: "bar" });
    const withToken = fetchSpy.mock.calls.filter(([, init]) => "Authorization" in (init.headers as Record<string, string>));
    expect(withToken).toHaveLength(1);
  });

  it("keeps the step of subscribing and what led there, as a slug", () => {
    vi.stubEnv("NODE_ENV", "production");
    track("Subscribe", { stage: "prompt", from: "Ask limit" });
    expect(sent().d).toBe("prompt:ask-limit");
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
