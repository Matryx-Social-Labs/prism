import { beforeEach, describe, expect, it, vi } from "vitest";

// A record folded into the one it duplicated answers /api/v1/events/<old> with a
// 308; fetch follows it, so the payload that comes back carries the SURVIVOR's
// id. The page must then send the reader (and the crawler) to the survivor's
// address permanently, not render the survivor under the old one.
const fetchEvent = vi.hoisted(() => vi.fn());
const permanentRedirect = vi.hoisted(() => vi.fn(() => { throw new Error("NEXT_REDIRECT"); }));
const notFound = vi.hoisted(() => vi.fn(() => { throw new Error("NEXT_NOT_FOUND"); }));
vi.mock("next/navigation", () => ({ permanentRedirect, notFound }));
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchEvent }));
vi.mock("@/components/StoryView", () => ({ StoryView: () => <main>the record</main> }));

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
  // The page streams (loading.tsx), so Next delivers the redirect as an
  // instant meta refresh with a 200, not an HTTP 308. The canonical is then the
  // one signal a crawler reads first: it must name the survivor, never the old
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
