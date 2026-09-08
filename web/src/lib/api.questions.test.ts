/**
 * The paying reader's token has to reach /questions.
 *
 * One suggested question is derived from story data — the cyber lens swaps in
 * "How is this being exploited in the wild?" when the CVE is KEV-listed — and
 * the server now serves it only to a reader who unlocked that lens. Without the
 * Authorization header the gate is closed for EVERYONE, so plugging the leak
 * would have quietly taken the question away from the people paying for it.
 */
import { describe, expect, it, vi, afterEach } from "vitest";

import { fetchQuestions } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubFetch() {
  const calls: Array<{ url: string; init: RequestInit }> = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return { ok: true, json: async () => ({ questions: ["q"] }) };
    }),
  );
  return calls;
}

describe("fetchQuestions", () => {
  it("sends the bearer token when the reader is signed in", async () => {
    const calls = stubFetch();
    await fetchQuestions("e1", "cyber", "tok");
    expect((calls[0].init.headers as Record<string, string>).Authorization).toBe("Bearer tok");
  });

  it("sends no Authorization header when anonymous", async () => {
    const calls = stubFetch();
    await fetchQuestions("e1", "cyber");
    expect(calls[0].init.headers).toEqual({});
  });

  it("stays uncached, so identity can never be shared through a cache entry", async () => {
    const calls = stubFetch();
    await fetchQuestions("e1", "cyber", "tok");
    expect(calls[0].init.cache).toBe("no-store");
  });
});
