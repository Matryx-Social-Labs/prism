import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const fetchSpy = vi.hoisted(() => vi.fn());
vi.mock("@/lib/analytics", () => ({ track: () => {} }));

import { adoptCookie, loadSession, saveSession, verifyMagicLink } from "@/lib/session";

const KEY = "prism.session.v1";

beforeEach(() => {
  localStorage.clear();
  fetchSpy.mockReset();
  vi.stubGlobal("fetch", fetchSpy);
});
afterEach(() => vi.unstubAllGlobals());

describe("the session is a cookie the page cannot read (audit C5)", () => {
  it("never writes a token to storage, even when handed one", () => {
    saveSession({ userId: "u1", email: "a@b.c", token: "secret" });
    expect(localStorage.getItem(KEY)).toBe(JSON.stringify({ userId: "u1", email: "a@b.c" }));
    expect(localStorage.getItem(KEY)).not.toContain("secret");
  });

  it("signs in with credentials so the browser keeps the cookie, and returns no token", async () => {
    fetchSpy.mockResolvedValue(new Response(JSON.stringify({ token: "raw", user_id: "u1", email: "a@b.c", needs_profile: false }), { status: 200 }));
    const r = await verifyMagicLink("link-token");
    expect(fetchSpy.mock.calls[0][1].credentials).toBe("include");
    expect(r.session).toEqual({ userId: "u1", email: "a@b.c" });
  });
});

describe("a page signed in before the cookie", () => {
  it("trades its stored token for the cookie, then forgets the token", async () => {
    localStorage.setItem(KEY, JSON.stringify({ token: "old", userId: "u1", email: "a@b.c" }));
    fetchSpy.mockResolvedValue(new Response(null, { status: 204 }));
    await adoptCookie();
    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toMatch(/\/api\/v1\/auth\/cookie$/);
    expect(init).toMatchObject({ method: "POST", credentials: "include", headers: { Authorization: "Bearer old" } });
    expect(loadSession()).toEqual({ userId: "u1", email: "a@b.c" });
  });
});
