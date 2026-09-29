import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { GET } from "@/app/go/[code]/route";

const go = (code: string) => GET(new NextRequest(`https://www.readprism.news/go/${code}`), { params: Promise.resolve({ code }) });

afterEach(() => vi.unstubAllGlobals());

describe("/go/<code>, a founder link's short address", () => {
  it("opens the link's page with its tags, and is never cached or indexed", async () => {
    const fetch = vi.fn<(url: string) => Promise<Response>>(async () => Response.json({ path: "/story/abc", tags: { utm_source: "whatsapp", utm_medium: "message", utm_content: "k3f9qa" } }));
    vi.stubGlobal("fetch", fetch);
    const res = await go("K3F9QA");
    expect(fetch.mock.calls[0][0]).toMatch(/\/api\/v1\/links\/k3f9qa$/);
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("https://www.readprism.news/story/abc?utm_source=whatsapp&utm_medium=message&utm_content=k3f9qa");
    expect(res.headers.get("cache-control")).toBe("no-store");
    expect(res.headers.get("x-robots-tag")).toBe("noindex");
  });

  it("opens the front page for a code that is not a link, without asking the API about a malformed one", async () => {
    const fetch = vi.fn(async () => new Response("", { status: 404 }));
    vi.stubGlobal("fetch", fetch);
    expect((await go("zzzzzz")).headers.get("location")).toBe("https://www.readprism.news/");
    expect((await go("../admin")).headers.get("location")).toBe("https://www.readprism.news/");
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("never leaves the site, whatever the API answers", async () => {
    for (const path of ["//evil.example/x", "/\\evil.example", "/\t/evil.example", "https://evil.example/"]) {
      vi.stubGlobal("fetch", vi.fn(async () => Response.json({ path, tags: {} })));
      expect((await go("k3f9qa")).headers.get("location"), path).toBe("https://www.readprism.news/");
    }
  });

  it("opens the front page while the API is away", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("fetch failed"); }));
    expect((await go("k3f9qa")).headers.get("location")).toBe("https://www.readprism.news/");
  });
});
