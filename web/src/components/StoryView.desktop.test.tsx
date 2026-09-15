import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { StoryView } from "@/components/StoryView";
import type { EventDetail } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchBrief: vi.fn(async () => null), fetchQuestions: vi.fn(async () => []) };
});
vi.mock("@/lib/lenses", () => ({
  useLenses: () => [{ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }],
  lensMeta: () => ({ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }),
}));

const EVENT = {
  id: "e1",
  title: "A story",
  summary: "A summary.",
  sector: "politics",
  subsector: null,
  image_url: null,
  regions: [],
  occurred_at: "2026-07-01T00:00:00Z",
  last_updated_at: "2026-07-01T00:00:00Z",
  projection: {},
  lens_briefs: { reader: "The reader take." },
  lens_points: {},
  available_lenses: ["reader"],
  coverage: null,
  entities: [],
  sources: [{ id: "s1", outlet: "The Hindu", url: "https://x.test/a", title: "A report" }],
  perspectives: [],
  impacts: [],
  claims: [],
} as unknown as EventDetail;

beforeEach(() => localStorage.clear());

/**
 * jsdom has no viewport, so both trees render and a plain getByText proves
 * nothing about which width sees a thing. What DOES carry the width is the
 * class: anything inside `.lg:hidden` is invisible on desktop. So these assert
 * on ancestry rather than presence.
 */
function hiddenOnDesktop(el: HTMLElement | null): boolean {
  return Boolean(el?.closest(".lg\\:hidden"));
}

describe("the desktop story page", () => {
  // REGRESSION: StoryDesktop was mounted self-closing, so the `children` slot
  // built to carry the evidence layer got nothing, and Perspectives, the
  // timeline, What to expect and every source lived only inside the lg:hidden
  // mobile tree. Desktop rendered a headline, a brief and a lens board and then
  // stopped — a story page with 35 sources showed none of them. The whole web
  // suite stayed green because these tests were scoped to the mobile tree.
  it.each(["Perspectives", "What to expect", "Sources"])(
    "renders %s outside the mobile-only tree, so desktop can see it",
    (heading) => {
      render(<StoryView event={EVENT} />);
      const found = screen
        .getAllByRole("heading")
        .find((h) => h.textContent?.includes(heading));
      expect(found, `no "${heading}" heading rendered at all`).toBeDefined();
      expect(
        hiddenOnDesktop(found as HTMLElement),
        `"${heading}" is inside .lg:hidden — invisible on desktop`,
      ).toBe(false);
    },
  );

  it("reaches the sources themselves on desktop, not just the heading", () => {
    render(<StoryView event={EVENT} />);
    const link = screen.getAllByText("A report")[0].closest("a, li") as HTMLElement;
    expect(hiddenOnDesktop(link)).toBe(false);
  });

  // REGRESSION: Ask had exactly one desktop mount and it sat in a rail marked
  // `hidden lg:flex` INSIDE the lg:hidden wrapper — a subtree that renders at no
  // width at all. The grounded agent was unreachable on desktop.
  it("gives desktop a way to reach Ask", () => {
    render(<StoryView event={EVENT} />);
    const asks = screen.getAllByText(/Ask/i).map((e) => e as HTMLElement);
    expect(asks.some((a) => !hiddenOnDesktop(a))).toBe(true);
  });
});
