/**
 * The lens meter needs an identity for a reader without an account: one id per
 * browser session, sent with every anonymous /brief (common/quota.py counts
 * three readings against it). A 402 says what would open the lens: an account
 * (signin_helps) or Plus.
 *
 * sessionStorage is stubbed as a global: jsdom's does not route through
 * Storage.prototype, so a prototype spy would never fire (CLAUDE.md).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchBrief } from "./api";

const store = new Map<string, string>();

beforeEach(() => {
  store.clear();
  vi.stubGlobal("sessionStorage", {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubFetch(status = 200, body: unknown = { lens: "markets", brief: "b", cached: true }) {
  const urls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      urls.push(url);
      return { ok: status < 400, status, json: async () => body };
    }),
  );
  return urls;
}

const anon = (url: string) => new URL(url).searchParams.get("anon_session");

describe("fetchBrief", () => {
  it("sends one session id for every anonymous reading, and none with an account", async () => {
    const urls = stubFetch();
    await fetchBrief("e1", "markets");
    await fetchBrief("e2", "cyber", null, false);
    await fetchBrief("e3", "markets", "tok");
    expect(anon(urls[0])).toMatch(/^[0-9a-f-]{36}$/);
    expect(anon(urls[1])).toBe(anon(urls[0]));
    expect(anon(urls[2])).toBeNull();
    expect(new URL(urls[1]).searchParams.get("generate")).toBe("false");
  });

  it("reads a spent anonymous meter as a way to sign in, and a spent account's as Plus", async () => {
    stubFetch(402, { detail: { used: 3, limit: 3, signin_helps: true, plus_helps: true } });
    expect(await fetchBrief("e1", "markets")).toEqual({ state: "signin_required", used: 3, limit: 3 });
    stubFetch(402, { detail: { used: 10, limit: 10, signin_helps: false, plus_helps: true } });
    expect(await fetchBrief("e1", "markets", "tok")).toEqual({ state: "limit", used: 10, limit: 10 });
  });
});
