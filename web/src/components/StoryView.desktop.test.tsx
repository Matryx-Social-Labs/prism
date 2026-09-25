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
  // built to carry the evidence layer got nothing, and every source lived only
  // inside the lg:hidden mobile tree. Desktop rendered a headline, a brief and
  // a lens board and then stopped — a story page with 35 sources showed none of
  // them. The whole web suite stayed green because these tests were scoped to
  // the mobile tree. (Perspectives and What to expect were retired in the
  // redesign — D4 — so Sources is the evidence section that remains here.)
  it.each(["Coverage", "The brief"])(
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

  it("reaches the reports themselves on desktop, not just the heading", () => {
    render(<StoryView event={EVENT} />);
    // The phone lists the reports under Coverage; the desktop lists them in the
    // evidence rail beside the record. At least one copy must be visible at lg.
    const copies = screen.getAllByText("A report").map((e) => e.closest("a, li") as HTMLElement);
    expect(copies.some((c) => !hiddenOnDesktop(c))).toBe(true);
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

/**
 * Tailwind display at a breakpoint, read off the class list: base `hidden`,
 * `lg:flex`, `xl:hidden`… applied in breakpoint order, last one wins; any
 * ancestor at display:none hides the element. jsdom cannot tell us this.
 */
const BPS = ["sm", "md", "lg", "xl"];
function visibleAt(el: HTMLElement | null, bp: string): boolean {
  const upTo = BPS.slice(0, BPS.indexOf(bp) + 1);
  for (let n = el; n; n = n.parentElement) {
    let shown = true;
    for (const c of n.className.split(/\s+/)) {
      const [pre, name] = c.includes(":") ? c.split(":") : ["", c];
      if (pre && !upTo.includes(pre)) continue;
      if (name === "hidden") shown = false;
      else if (/^(block|flex|grid|inline-flex|inline|contents)$/.test(name)) shown = true;
    }
    if (!shown) return false;
  }
  return true;
}

describe("the two-column width (1024–1279px)", () => {
  // REGRESSION: the evidence rail switched on at lg with a fixed 300px track
  // beside a 220px rail, which left the reading column 360px at 1024: a
  // five-line headline and an 80px photo tile. The rail now waits for xl, so
  // at lg the reports must be reachable INLINE, and at xl in the rail.
  it.each(["lg", "xl"])("still shows the reports at %s", (bp) => {
    render(<StoryView event={EVENT} />);
    const copies = screen.getAllByText("A report").map((e) => e.closest("a, li") as HTMLElement);
    expect(copies.some((c) => visibleAt(c, bp)), `no copy of the reports is visible at ${bp}`).toBe(true);
  });
});
