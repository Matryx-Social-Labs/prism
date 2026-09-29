// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";
import { SITE_URL } from "@/lib/site";
import { GET } from "./route";

afterEach(() => vi.unstubAllGlobals());

// Audit 01 P2-11: lastmod is the API's content clock (the newest report), and
// an API from before the rename still gets a lastmod rather than none.
describe("records-sitemap.xml", () => {
  it("prints each record's content lastmod, and an older API's field until it deploys", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ records: [
      { id: "e1", lastmod: "2026-09-20T08:00:00+00:00" },
      { id: "e2", last_updated_at: "2026-09-24T14:00:00+00:00" },
      { id: "e3", lastmod: null },
    ] })));
    const xml = await (await GET()).text();
    expect(xml).toContain(`<url><loc>${SITE_URL}/story/e1</loc><lastmod>2026-09-20T08:00:00+00:00</lastmod></url>`);
    expect(xml).toContain(`<url><loc>${SITE_URL}/story/e2</loc><lastmod>2026-09-24T14:00:00+00:00</lastmod></url>`);
    expect(xml).toContain(`<url><loc>${SITE_URL}/story/e3</loc></url>`);
  });
});
