import { describe, expect, it } from "vitest";
import type { FeedItem } from "@/lib/api";
import { todaySections } from "@/lib/today";

// Today showed its five most-reported records twice: a card rail on top, then
// the same five again at the head of the list (2026-11-02). Each record now
// appears exactly once: the lead, the next four, then one section each.
const rec = (id: string, source_count: number, over: Partial<FeedItem> = {}) =>
  ({ id, title: id, source_count, sector: "politics", subject_path: "politics.elections", regions: ["IN"], last_updated_at: "2026-11-02T10:00:00Z", outlets: [], ...over }) as unknown as FeedItem;

const ids = (xs: FeedItem[]) => xs.map((x) => x.id);

describe("todaySections", () => {
  const items = [
    rec("p1", 20), rec("p2", 15), rec("b1", 12, { sector: "business", subject_path: "business.markets" }), rec("p3", 11), rec("w1", 10, { regions: ["US"] }),
    rec("p4", 9), rec("ka1", 8, { regions: ["IN", "IN-KA"] }), rec("b2", 7, { sector: "business", subject_path: "business.markets" }), rec("w2", 6, { regions: ["GB"] }), rec("u1", 5, { sector: null, subject_path: null, regions: [] }),
  ];

  it("leads with the most reported, then the next four, and never repeats a record", () => {
    const t = todaySections(items, { state: null });
    expect(t.lead?.id).toBe("p1");
    expect(ids(t.next)).toEqual(["p2", "b1", "p3", "w1"]);
    const all = [t.lead!.id, ...ids(t.next), ...t.sections.flatMap((s) => ids(s.items))];
    expect(new Set(all).size).toBe(all.length);
    expect(all).toHaveLength(items.length);
  });

  it("puts India's records under their subjects in the nav's order and the world's in its own section, last", () => {
    const t = todaySections(items, { state: null });
    expect(t.sections.map((s) => s.title)).toEqual(["Politics", "Business & Markets", "Not yet placed in a subject", "World"]);
    expect(ids(t.sections.at(-1)!.items)).toEqual(["w2"]);
    expect(t.sections[0].href).toBe("/sector/politics");
  });

  it("gives the reader's state its own section first when they have set one", () => {
    const t = todaySections(items, { state: "IN-KA", stateName: "Karnataka" });
    expect(t.sections[0]).toMatchObject({ key: "state", title: "Karnataka", href: "/state/karnataka" });
    expect(ids(t.sections[0].items)).toEqual(["ka1"]);
    expect(t.sections.slice(1).flatMap((s) => ids(s.items))).not.toContain("ka1");
  });

  it("shows a few per section and counts the rest, linking where the rest are", () => {
    const many = [rec("lead", 99), ...Array.from({ length: 4 }, (_, i) => rec(`n${i}`, 90 - i)), ...Array.from({ length: 9 }, (_, i) => rec(`p${i}`, 50 - i))];
    const politics = todaySections(many, { state: null, perSection: 6 }).sections[0];
    expect(politics.items).toHaveLength(6);
    expect(politics.total).toBe(9);
  });

  it("is empty, not broken, on an empty day", () => {
    expect(todaySections([], { state: null })).toEqual({ lead: null, next: [], sections: [] });
  });
});
