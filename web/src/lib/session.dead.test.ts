import { afterEach, beforeEach, expect, it, vi } from "vitest";

// A separate file: adoptCookie runs once per page load (module state).
const fetchSpy = vi.hoisted(() => vi.fn());
vi.mock("@/lib/analytics", () => ({ track: () => {} }));

import { adoptCookie, loadSession } from "@/lib/session";

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("fetch", fetchSpy);
});
afterEach(() => vi.unstubAllGlobals());

it("signs the page out when its stored token is already dead", async () => {
  localStorage.setItem("prism.session.v1", JSON.stringify({ token: "dead", userId: "u1", email: "a@b.c" }));
  fetchSpy.mockResolvedValue(new Response(null, { status: 401 }));
  await adoptCookie();
  expect(loadSession()).toBeNull();
});
