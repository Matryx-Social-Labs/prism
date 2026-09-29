import { describe, expect, it, vi } from "vitest";
import type { Metadata } from "next";

// The layout calls next/font at import; any face is just a variable name here.
vi.mock("next/font/google", async () => {
  const { readFileSync } = await import("node:fs");
  const names = readFileSync(`${process.cwd()}/src/app/layout.tsx`, "utf8").match(/import \{([^}]+)\} from "next\/font\/google"/)![1];
  return Object.fromEntries(names.split(",").map((f) => [f.trim(), () => ({ variable: f.trim() })]));
});

import { metadata as root } from "@/app/layout";
import { metadata as home } from "@/app/page";
import { metadata as about } from "@/app/about/page";
import { metadata as plus } from "@/app/plus/page";
import { metadata as feed } from "@/app/feed/layout";
import { metadata as trending } from "@/app/trending/layout";
import { metadata as sources } from "@/app/sources/page";
import { metadata as corrections } from "@/app/corrections/page";
import { metadata as pulse } from "@/app/pulse/layout";
import { metadata as privacy } from "@/app/privacy/page";
import { metadata as terms } from "@/app/terms/page";
import { metadata as refunds } from "@/app/refunds/page";

// Audit 2026-09-29: the root layout set og:url "/" and the landing's title, so
// a share of /sources, /corrections or a sector page showed the homepage's
// card and address. Each page now names itself; the layout names only the site.
const og = (m: Metadata) => m.openGraph as { url?: string; title?: string } | undefined;

describe("share cards", () => {
  it("leaves the page's own title and address out of the layout", () => {
    expect(og(root)?.url).toBeUndefined();
    expect(og(root)?.title).toBeUndefined();
  });

  it.each([
    ["/", home], ["/about", about], ["/plus", plus], ["/feed", feed], ["/trending", trending], ["/sources", sources],
    ["/corrections", corrections], ["/pulse", pulse], ["/privacy", privacy], ["/terms", terms], ["/refunds", refunds],
  ] as const)("%s shares its own address and a title", (path, m) => {
    expect(m.alternates?.canonical).toBe(path);
    expect(og(m)?.url).toBe(path);
    expect(og(m)?.title).toBeTruthy();
  });
});
