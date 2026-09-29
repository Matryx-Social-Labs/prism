import { beforeEach, describe, expect, it, vi } from "vitest";

// A record folded into the one it duplicated answers /api/v1/events/<old> with a
// 308; fetch follows it, so the payload that comes back carries the SURVIVOR's
// id. The page must then send the reader (and the crawler) to the survivor's
// address permanently, not render the survivor under the old one.
const fetchEvent = vi.hoisted(() => vi.fn());
const permanentRedirect = vi.hoisted(() => vi.fn(() => { throw new Error("NEXT_REDIRECT"); }));
const notFound = vi.hoisted(() => vi.fn(() => { throw new Error("NEXT_NOT_FOUND"); }));
vi.mock("next/navigation", () => ({ permanentRedirect, notFound }));
const fetchSubjects = vi.hoisted(() => vi.fn(async () => null));
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchEvent, fetchSubjects }));
vi.mock("@/components/StoryView", () => ({
  StoryView: ({ trail }: { trail?: unknown }) => <main data-trail={JSON.stringify(trail ?? null)}>the record</main>,
}));

import StoryPage, { generateMetadata } from "@/app/story/[id]/page";
import QuotePage, { generateMetadata as quoteMetadata } from "@/app/story/[id]/quote/[n]/page";

const record = (id: string) => ({ id, title: "Bridge closes", sector: null, sources: [], claims: [], entities: [] });
const params = (id: string, n?: string) => ({ params: Promise.resolve({ id, n: n ?? "0-0" }) });

beforeEach(() => {
  fetchEvent.mockReset();
  permanentRedirect.mockClear();
});

describe("/story/<id> — a merged record's address", () => {
  it("redirects permanently to the record it was merged into", async () => {
    fetchEvent.mockResolvedValue(record("survivor"));
    await expect(StoryPage(params("absorbed"))).rejects.toThrow("NEXT_REDIRECT");
    expect(permanentRedirect).toHaveBeenCalledWith("/story/survivor");
  });

  it("renders a record at its own address", async () => {
    fetchEvent.mockResolvedValue(record("survivor"));
    expect(await StoryPage(params("survivor"))).toBeTruthy();
    expect(permanentRedirect).not.toHaveBeenCalled();
  });

  it("sends a merged record's quote link to the survivor's record: a quote's number is its place in one record", async () => {
    fetchEvent.mockResolvedValue(record("survivor"));
    await expect(QuotePage(params("absorbed", "1-2"))).rejects.toThrow("NEXT_REDIRECT");
    expect(permanentRedirect).toHaveBeenCalledWith("/story/survivor");
  });
});

describe("/story/<id> — the merged address's metadata", () => {
  // The redirect is an HTTP 308 now that the route no longer streams (its
  // loading.tsx put the metadata in <body> and turned 404s into 200s,
  // 2026-09-29), but the canonical must still name the survivor, never the old
  // address it is leaving (seen live on the first 20 merges, 2026-09-27).
  it("names the survivor as canonical, not the absorbed address", async () => {
    fetchEvent.mockResolvedValue(record("survivor"));
    const meta = await generateMetadata(params("absorbed"));
    expect(meta.alternates?.canonical).toBe("/story/survivor");
    expect((meta.openGraph as { url?: string } | undefined)?.url).toBe("/story/survivor");
  });

  it("points a merged record's quote page at the survivor's record", async () => {
    const claim = { id: "q1", quote_text: "The bridge stays shut until the audit is done.", source_name: "The Hindu" };
    fetchEvent.mockResolvedValue({ ...record("survivor"), claims: [{ speaker: "A Minister", role: null, claims: [claim] }] });
    const meta = await quoteMetadata(params("absorbed", "q1"));
    expect(meta.alternates?.canonical).toBe("/story/survivor");
    expect(JSON.stringify(meta)).not.toContain("absorbed");
  });
});

// Audit A2 and A9: records printed their subject as text, and their breadcrumb
// named only the sector group, so the subject pages under the six groups had no
// path from the records they list.
describe("/story/<id> — the record's place in the subject tree", () => {
  const html = async (id: string) => (await import("react-dom/server")).renderToString(await StoryPage(params(id)));
  const crumbs = (page: string) => {
    const lists = [...page.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/g)].map((m) => JSON.parse(m[1]));
    const trail = lists.find((l) => l["@type"] === "BreadcrumbList");
    return trail.itemListElement.map((i: { name: string; item: string }) => [i.name, new URL(i.item).pathname]);
  };
  const trailProp = (page: string) => JSON.parse(new DOMParser().parseFromString(page, "text/html").querySelector("main")!.dataset.trail!);

  it("follows the subject path in its structured data, and hands the page the same trail to print and link", async () => {
    fetchEvent.mockResolvedValue({ ...record("r1"), sector: "politics", subject_path: "politics.elections" });
    fetchSubjects.mockResolvedValueOnce({
      roots: [],
      nodes: [
        { path: "politics", slug: "politics", label: "Politics", depth: 1, story_count: 9 },
        { path: "politics.elections", slug: "elections", label: "Elections", depth: 2, story_count: 4 },
      ],
    } as never);
    const page = await html("r1");
    expect(crumbs(page)).toEqual([["Prism", "/"], ["Politics", "/sector/politics"], ["Elections", "/subject/politics/elections"], ["Bridge closes", "/story/r1"]]);
    expect(trailProp(page)).toEqual([{ name: "Politics", href: "/sector/politics" }, { name: "Elections", href: "/subject/politics/elections" }]);
  });

  it("names the sector group when the subject tree cannot be read", async () => {
    fetchEvent.mockResolvedValue({ ...record("r1"), sector: "politics", subject_path: "politics.elections" });
    fetchSubjects.mockRejectedValueOnce(new Error("api down"));
    expect(crumbs(await html("r1"))).toEqual([["Prism", "/"], ["Politics", "/sector/politics"], ["Bridge closes", "/story/r1"]]);
  });
});
