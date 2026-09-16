import { describe, expect, it } from "vitest";
import { headlineByline } from "@/lib/headline";

const src = (source_name: string) => ({ article_id: "a", source_slug: "s", source_name, title: "t", url: null, published_at: null, language: "en", stance: null, funding: null });

describe("headlineByline — whose words the title is", () => {
  it("says Prism wrote it, from how many reports, when the record says so", () => {
    expect(headlineByline({ headline_by: "prism", sources: [src("A"), src("B")] })).toBe("Headline by Prism · from 2 reports");
  });
  it("names the outlet whose headline it is otherwise", () => {
    expect(headlineByline({ headline_by: null, sources: [src("The Hindu")] })).toBe("Headline as filed by The Hindu · 1 report");
  });
});
