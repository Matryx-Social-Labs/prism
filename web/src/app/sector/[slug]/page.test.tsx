import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToString } from "react-dom/server";

const fetchFeed = vi.hoisted(() => vi.fn());
const fetchSubjects = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchFeed, fetchSubjects }));

import SectorPage from "@/app/sector/[slug]/page";

const node = (path: string, label: string) => ({ path, slug: path.split(".").pop()!, label, depth: path.split(".").length, story_count: 3 });
const TREE = {
  roots: [],
  nodes: [
    node("politics", "Politics"), node("politics.elections", "Elections"), node("politics.elections.state", "State elections"),
    node("politics.governance", "Governance"), node("sports", "Sports"), node("sports.cricket", "Cricket"),
  ],
};
const page = async (slug: string) =>
  new DOMParser().parseFromString(renderToString(await SectorPage({ params: Promise.resolve({ slug }) })), "text/html");
const chips = (doc: Document) =>
  [...doc.querySelectorAll('nav[aria-label="Sub-topics"] a')].map((a) => [a.textContent, a.getAttribute("href")]);

beforeEach(() => {
  fetchFeed.mockReset().mockResolvedValue([]);
  fetchSubjects.mockReset().mockResolvedValue(TREE);
});

// Audit A1: the subject pages under the six groups were in the sitemap and
// linked from nowhere a crawler starts — the strip sends each group to its
// sector page, and the sector page printed no sub-topics.
describe("/sector/<slug> — the group's sub-topics", () => {
  it("links the group's own children, under the heading, and no grandchild or other group's", async () => {
    const doc = await page("politics");
    expect(chips(doc)).toEqual([
      ["All", "/sector/politics"],
      ["Elections", "/subject/politics/elections"],
      ["Governance", "/subject/politics/governance"],
    ]);
    const h1 = doc.querySelector("h1")!;
    expect(h1.compareDocumentPosition(doc.querySelector('nav[aria-label="Sub-topics"]')!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("resolves a legacy pipeline slug to its group's sub-topics", async () => {
    fetchSubjects.mockResolvedValue({ roots: [], nodes: [node("business", "Business & Markets"), node("business.banking", "Banking")] });
    expect(chips(await page("finance"))).toEqual([["All", "/sector/business"], ["Banking", "/subject/business/banking"]]);
  });

  it("renders the chart without chips when the subject tree cannot be read", async () => {
    fetchSubjects.mockRejectedValue(new Error("api down"));
    const doc = await page("politics");
    expect(chips(doc)).toEqual([]);
    expect(doc.querySelector("h1")?.textContent).toContain("Politics");
  });
});
