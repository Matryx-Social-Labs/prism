import { beforeEach, describe, expect, it, vi } from "vitest";

import { cardForPath } from "@/lib/cards";

const fetchEvent = vi.hoisted(() => vi.fn());
const fetchEntity = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async (orig) => ({
  ...(await orig<typeof import("@/lib/api")>()),
  fetchEvent, fetchEntity, fetchSources: async () => ({ outlets: 41 }), fetchTrendingStory: async () => null,
}));

beforeEach(() => {
  fetchEvent.mockReset().mockResolvedValue({ title: "A headline", sources: [{ publisher: "a", origin: "national", language: "en", published_at: "2026-09-28T01:00:00Z" }], sector: null, last_updated_at: "2026-09-28T01:00:00Z", monitored_outlets: 41, claims: [], quote_aliases: {} });
  fetchEntity.mockReset().mockResolvedValue(null);
});

describe("which card a /card path draws", () => {
  // The route is public and every render costs CPU: a path that is not a real
  // page's card must be refused before anything is fetched or drawn.
  it("draws nothing, and fetches nothing, for a path that is not a page's card", async () => {
    const junk = [["a1"], ["story", "not an id"], ["story", "7f9d86ff-1234", "extra"], ["story", "7f9d86ff-1234", "quote", "q 1"],
      ["entity", "a/b"], ["entity", "x", "y"], ["plus"], ["site", "x"], ["story", "7f9d86ff-1234", "quote", "q1", "more"], []];
    for (const path of junk) expect(await cardForPath(path, "portrait"), path.join("/")).toBeNull();
    expect(fetchEvent).not.toHaveBeenCalled();
    expect(fetchEntity).not.toHaveBeenCalled();
  });

  it("draws a real page's card, the brand card at site, and nothing for a page that is not there", async () => {
    expect((await cardForPath(["story", "7f9d86ff-1234-4abc"], "story"))?.text).toContain("A headline");
    expect(await cardForPath(["site"], "portrait")).not.toBeNull();
    expect(await cardForPath(["entity", "नाम"], "portrait")).toBeNull(); // any script's slug is asked for; this one is not there
    expect(fetchEntity).toHaveBeenCalledWith("नाम");
  });
});
