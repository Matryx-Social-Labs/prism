import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StoryView } from "@/components/StoryView";
import type { EventDetail } from "@/lib/api";

const fetchBrief = vi.hoisted(() => vi.fn<(...args: unknown[]) => Promise<unknown>>(async () => null));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchBrief, fetchQuestions: vi.fn(async () => []) };
});
vi.mock("@/lib/lenses", async () => ({
  ...(await vi.importActual<typeof import("@/lib/lenses")>("@/lib/lenses")),
  useLenses: () => [
    { slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" },
    { slug: "cyber", short: "Cyber", color: "#06B6D4", bg: "#e0f7fa", tagline: "t" },
  ],
  lensMeta: (slug: string) =>
    slug === "cyber"
      ? { slug: "cyber", short: "Cyber", color: "#06B6D4", bg: "#e0f7fa", tagline: "t" }
      : { slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" },
}));


// jsdom applies no CSS, so the desktop composition and the mobile tree BOTH
// render and the brief text appears twice. These tests are about the mobile
// controls — the pinned rail and the number keys — so scope to that tree rather
// than loosening the assertions to "appears somewhere".
function mobile() {
  const root = document.querySelector("article");
  if (!root) throw new Error("mobile tree not found");
  return within(root as HTMLElement);
}

const READER_BRIEF = "The reader take on this story.";
const CYBER_BRIEF = "The cyber take on this story.";

function event(over: Partial<EventDetail> = {}): EventDetail {
  return {
    id: "e1",
    title: "A story",
    summary: "A summary.",
    sector: "cybersecurity",
    subsector: null,
    image_url: null,
    regions: [],
    occurred_at: "2026-07-01T00:00:00Z",
    last_updated_at: "2026-07-01T00:00:00Z",
    projection: {},
    lens_briefs: { reader: READER_BRIEF, cyber: CYBER_BRIEF },
    lens_points: {},
    available_lenses: ["reader", "cyber"],
    coverage: null,
    entities: [],
    sources: [],
    perspectives: [],
    impacts: [],
  claims: [],
    ...over,
  } as unknown as EventDetail;
}

// jsdom implements no scrollIntoView, and the pinned rail calls it on every
// pick — without this the tap throws instead of flipping.
const scrollIntoView = vi.fn();

beforeEach(() => {
  localStorage.clear();
  fetchBrief.mockReset().mockResolvedValue(null);
  scrollIntoView.mockClear();
  Element.prototype.scrollIntoView = scrollIntoView;
});

describe("lens flip — keyboard", () => {
  // The desktop flip binds to 1/2/3 (the brief header prints "PRESS 1 · 2 · 3").
  // It routes through the same pickLens as the tabs, so ISSUE-004's dead-button
  // regression killed it too — and nothing covered it.
  it("flips a signed-out reader with the number key, no scroll", async () => {
    render(<StoryView event={event()} />);
    expect(await mobile().findByText(READER_BRIEF)).toBeInTheDocument();

    await userEvent.keyboard("2");

    await waitFor(() =>
      expect(screen.getAllByRole("tab", { name: /Cyber/ })[0]).toHaveAttribute(
        "aria-selected",
        "true",
      ),
    );
    await waitFor(() => expect(fetchBrief).toHaveBeenCalledWith("e1", "cyber", undefined, false));
    // "layout never moves": a key press must not yank the page.
    expect(scrollIntoView).not.toHaveBeenCalled();
  });

  // ⌘2 is "second browser tab", ⌥2 types a character — and the handler calls
  // preventDefault(), so a missing modifier guard doesn't just flip the lens,
  // it eats the reader's own shortcut. ⌘1 can't show this: index 0 is Reader,
  // which is already selected, so both branches look identical.
  it.each(["{Meta>}2{/Meta}", "{Control>}2{/Control}", "{Alt>}2{/Alt}"])(
    "ignores %s — the modifier belongs to the browser",
    async (keys) => {
      render(<StoryView event={event()} />);
      expect(await mobile().findByText(READER_BRIEF)).toBeInTheDocument();

      await userEvent.keyboard(keys);

      expect(screen.getAllByRole("tab", { name: /Reader/ })[0]).toHaveAttribute(
        "aria-selected",
        "true",
      );
      expect(mobile().getByText(READER_BRIEF)).toBeInTheDocument();
    },
  );

  // The header prints the keys this story actually offers. Anything outside that
  // range must fall through to the page — pickLens(offered[8]) is `undefined`,
  // which reads as "no lens" and empties the brief the reader was reading.
  it.each(["0", "9"])("ignores %s, which is no lens at all", async (key) => {
    render(<StoryView event={event()} />);
    expect(await mobile().findByText(READER_BRIEF)).toBeInTheDocument();

    await userEvent.keyboard(key);

    expect(mobile().getByText(READER_BRIEF)).toBeInTheDocument();
    expect(screen.getAllByRole("tab", { name: /Reader/ })[0]).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("leaves the keys alone while the reader is typing", async () => {
    render(
      <>
        <input aria-label="search" />
        <StoryView event={event()} />
      </>,
    );
    await mobile().findByText(READER_BRIEF);

    await userEvent.type(screen.getByLabelText("search"), "2");

    expect(screen.getByLabelText("search")).toHaveValue("2");
    expect(screen.getAllByRole("tab", { name: /Reader/ })[0]).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

});

describe("lens flip — pinned mobile rail", () => {
  // The rail sits in the thumb zone with the brief scrolled off-screen, so the
  // pick has to bring the result into view or it reads as a dead button.
  it("flips and scrolls the brief into view", async () => {
    render(<StoryView event={event()} />);
    await mobile().findByText(READER_BRIEF);

    // The pinned rail is the one tablist on the page; the desk's lens board uses aria-pressed.
    await userEvent.click(screen.getByRole("tab", { name: /Cyber/ }));

    await waitFor(() =>
      expect(screen.getByRole("tab", { name: /Cyber/ })).toHaveAttribute("aria-selected", "true"),
    );
    expect(scrollIntoView).toHaveBeenCalledWith(
      expect.objectContaining({ behavior: "smooth", block: "start" }),
    );
  });

  it("jumps instantly when the reader asked for reduced motion", async () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: true, // prefers-reduced-motion: reduce
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    }));
    render(<StoryView event={event()} />);
    await mobile().findByText(READER_BRIEF);

    await userEvent.click(screen.getByRole("tab", { name: /Cyber/ }));

    expect(scrollIntoView).toHaveBeenCalledWith(expect.objectContaining({ behavior: "auto" }));
  });
});

describe("locked lens", () => {
  // Free tier discipline: past the meter a tap asks once, for what is written,
  // and never for a brief to be generated. Every signed-out visitor tapping
  // Cyber would otherwise bill an LLM call.
  it("asks a signed-out reader past the meter to sign in, and generates nothing", async () => {
    render(<StoryView event={event({ lens_briefs: { reader: READER_BRIEF } } as Partial<EventDetail>)} />);
    await mobile().findByText(READER_BRIEF);
    fetchBrief.mockClear();
    fetchBrief.mockResolvedValue({ state: "signin_required", used: 3, limit: 3 });

    await userEvent.click(screen.getAllByRole("tab", { name: /Cyber/ })[0]);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Sign in to keep reading" })).toBeInTheDocument(),
    );
    expect(fetchBrief.mock.calls).toEqual([["e1", "cyber", undefined, false]]);
  });
});

describe("story timeline ownership", () => {
  // The event page used to render StoryTimeline off story_timeline(event_id) —
  // the LIVE partition — while /trending/[slug] renders the same arc off the
  // story's FROZEN member_event_ids. Two member sets for one story, so the two
  // pages could disagree about which developments exist. The story page owns the
  // arc now. This test is the boundary: it fails the moment the event page starts
  // rendering a timeline again, even from a payload that still carries one.
  const STORY_WITH_SIBLINGS = {
    developments: [
      { id: "e0", title: "How it started", sector: null, occurred_at: "2026-06-28T00:00:00Z", image_url: null, is_current: false, why: null },
      { id: "e1", title: "A story", sector: null, occurred_at: "2026-07-01T00:00:00Z", image_url: null, is_current: true, why: null },
    ],
    cast: ["Someone"],
  };

  it("renders no timeline even when the payload carries sibling developments", async () => {
    // Passed through the cast, so a server still emitting `story` cannot revive
    // the section by accident — the component has to ignore it.
    render(<StoryView event={event({ story: STORY_WITH_SIBLINGS } as unknown as Partial<EventDetail>)} />);
    // Wait for a real render before asserting an absence, or this passes vacuously.
    expect(await mobile().findByText(READER_BRIEF)).toBeInTheDocument();

    expect(screen.queryByText("The story so far")).not.toBeInTheDocument();
    expect(screen.queryByText("How it started")).not.toBeInTheDocument();
    expect(document.getElementById("story-so-far")).toBeNull();
  });

  it("keeps the section out of the mobile anchor nav", async () => {
    render(<StoryView event={event({ story: STORY_WITH_SIBLINGS } as unknown as Partial<EventDetail>)} />);
    expect(await mobile().findByText(READER_BRIEF)).toBeInTheDocument();

    // Coverage still anchors, so the nav itself is proven to render.
    const nav = screen.getByRole("complementary", { name: "On this story" });
    expect(within(nav).getByRole("link", { name: /Coverage/ })).toBeInTheDocument();
    expect(within(nav).queryByRole("link", { name: /The story so far/ })).not.toBeInTheDocument();
  });
});

// Marketing screenshots the record on a phone, so its bar carries the lockup (founder pick B,
// 2026-09-28): the way back is an arrow named for Today, and readPrism.news sits centred.
describe("the record's phone bar", () => {
  it("is an arrow back to Today and the lockup", () => {
    render(<StoryView event={event()} />);
    const back = screen.getByRole("link", { name: "Back to today" });
    expect(back).toHaveAttribute("href", "/feed");
    expect(back).not.toHaveTextContent("Today");
    expect(back.parentElement).toContainElement(screen.getAllByRole("link", { name: "readPrism.news" })[0]);
  });
});
