import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchEntity, fetchEvent, fetchSubject, fetchTrendingStory, NotFound, unlessMissing } from "@/lib/api";

// Search Console, 2026-11-02: twelve live records were reported "Not found (404)",
// all last crawled during the October database outages. The page fetchers read
// any failed response as "no such page", so a 500 from the API went out as a 404
// and Google was told the records were gone. Only an API 404 means missing now.
const answer = (status: number) => vi.stubGlobal("fetch", vi.fn(async () => new Response(status === 200 ? "{}" : "x", { status })));

afterEach(() => vi.unstubAllGlobals());

describe.each([
  ["fetchTrendingStory", () => fetchTrendingStory("s")],
  ["fetchEntity", () => fetchEntity("e")],
  ["fetchSubject", () => fetchSubject("politics")],
])("%s", (_name, call) => {
  it("answers null only when the API says there is no such page", async () => {
    answer(404);
    await expect(call()).resolves.toBeNull();
  });
  it("throws when the API fails, so the page is a 5xx and not a 404", async () => {
    answer(500);
    await expect(call()).rejects.toThrow();
  });
});

describe("fetchEvent", () => {
  it("throws NotFound on an API 404, which unlessMissing reads as null", async () => {
    answer(404);
    await expect(fetchEvent("x")).rejects.toBeInstanceOf(NotFound);
    await expect(unlessMissing(fetchEvent("x"))).resolves.toBeNull();
  });
  it("lets any other failure through unlessMissing", async () => {
    answer(503);
    await expect(unlessMissing(fetchEvent("x"))).rejects.not.toBeInstanceOf(NotFound);
  });
});
