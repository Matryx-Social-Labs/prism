import { beforeEach, describe, expect, it, vi } from "vitest";

// A page that cannot reach the API must fail (Next answers 5xx: try again), never
// call notFound() (404: gone) or ask not to be indexed. Twelve live records sat
// in Search Console's "Not found (404)" after the October outages (2026-11-02).
const api = vi.hoisted(() => ({
  fetchEvent: vi.fn(), fetchTrendingStory: vi.fn(), fetchEntity: vi.fn(), fetchSubject: vi.fn(),
  fetchStateHub: vi.fn(), fetchFeed: vi.fn(), fetchSubjects: vi.fn(), fetchStateHubs: vi.fn(), fetchTrending: vi.fn(),
}));
const notFound = vi.hoisted(() => vi.fn(() => { throw new Error("NEXT_NOT_FOUND"); }));
vi.mock("next/navigation", () => ({ notFound, redirect: vi.fn(), permanentRedirect: vi.fn() }));
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), ...api }));

import { NotFound } from "@/lib/api";
import StoryPage from "@/app/story/[id]/page";
import QuotePage, { generateMetadata as quoteMeta } from "@/app/story/[id]/quote/[n]/page";
import TrendingStoryPage from "@/app/trending/[slug]/page";
import EntityPage from "@/app/entity/[slug]/page";
import SubjectPageRoute from "@/app/subject/[...path]/page";
import StateHubRoute, { generateMetadata as stateMeta } from "@/app/state/[slug]/page";

const down = new Error("api down");
const p = <T,>(v: T) => ({ params: Promise.resolve(v) });

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset().mockRejectedValue(down));
  notFound.mockClear();
});

describe.each([
  ["a record", () => StoryPage(p({ id: "r" })), () => api.fetchEvent.mockRejectedValue(new NotFound("event 404"))],
  ["a quote", () => QuotePage(p({ id: "r", n: "1" })), () => api.fetchEvent.mockRejectedValue(new NotFound("event 404"))],
  ["a story", () => TrendingStoryPage(p({ slug: "s" })), () => api.fetchTrendingStory.mockResolvedValue(null)],
  ["an actor", () => EntityPage(p({ slug: "e" })), () => api.fetchEntity.mockResolvedValue(null)],
  ["a subject", () => SubjectPageRoute(p({ path: ["politics"] })), () => api.fetchSubject.mockResolvedValue(null)],
])("%s page", (_kind, render, missing) => {
  it("fails when the API is down, and does not say the page is gone", async () => {
    await expect(render()).rejects.toBe(down);
    expect(notFound).not.toHaveBeenCalled();
  });
  it("is a 404 when the API says there is no such page", async () => {
    missing();
    await expect(render()).rejects.toThrow("NEXT_NOT_FOUND");
  });
});

it("a quote's metadata fails with the API rather than titling the page 'not found'", async () => {
  await expect(quoteMeta(p({ id: "r", n: "1" }))).rejects.toBe(down);
});

it("a state page fails when the API is down instead of serving itself as noindex", async () => {
  await expect(stateMeta(p({ slug: "goa" }))).rejects.toBe(down);
  await expect(StateHubRoute(p({ slug: "goa" }))).rejects.toBe(down);
});
