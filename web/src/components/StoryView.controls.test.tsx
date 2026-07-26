import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StoryView } from "@/components/StoryView";
import type { EventDetail } from "@/lib/api";

const fetchBrief = vi.hoisted(() => vi.fn(async () => null));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchBrief, fetchQuestions: vi.fn(async () => []) };
});
vi.mock("@/lib/lenses", () => ({
  useLenses: () => [
    { slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" },
    { slug: "cyber", short: "Cyber", color: "#06B6D4", bg: "#e0f7fa", tagline: "t" },
  ],
  lensMeta: (slug: string) =>
    slug === "cyber"
      ? { slug: "cyber", short: "Cyber", color: "#06B6D4", bg: "#e0f7fa", tagline: "t" }
      : { slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" },
}));

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
    thread: null,
    related: [],
    story: { developments: [] },
    sources: [],
    perspectives: [],
    impacts: [],
    ...over,
  } as unknown as EventDetail;
}

// jsdom implements no scrollIntoView, and the pinned rail calls it on every
// pick — without this the tap throws instead of flipping.
const scrollIntoView = vi.fn();

beforeEach(() => {
  localStorage.clear();
  fetchBrief.mockClear();
  scrollIntoView.mockClear();
  Element.prototype.scrollIntoView = scrollIntoView;
});

describe("lens flip — keyboard", () => {
  // The desktop flip binds to 1/2/3 (the brief header prints "PRESS 1 · 2 · 3").
  // It routes through the same pickLens as the tabs, so ISSUE-004's dead-button
  // regression killed it too — and nothing covered it.
  it("flips a signed-out reader with the number key, no scroll", async () => {
    render(<StoryView event={event()} />);
    expect(await screen.findByText(READER_BRIEF)).toBeInTheDocument();

    await userEvent.keyboard("2");

    await waitFor(() =>
      expect(screen.getAllByRole("tab", { name: /Cyber/ })[0]).toHaveAttribute(
        "aria-selected",
        "true",
      ),
    );
    expect(screen.getByRole("button", { name: /Sign in to unlock/ })).toBeInTheDocument();
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
      expect(await screen.findByText(READER_BRIEF)).toBeInTheDocument();

      await userEvent.keyboard(keys);

      expect(screen.getAllByRole("tab", { name: /Reader/ })[0]).toHaveAttribute(
        "aria-selected",
        "true",
      );
      expect(screen.getByText(READER_BRIEF)).toBeInTheDocument();
    },
  );

  // The header prints the keys this story actually offers. Anything outside that
  // range must fall through to the page — pickLens(offered[8]) is `undefined`,
  // which reads as "no lens" and empties the brief the reader was reading.
  it.each(["0", "9"])("ignores %s, which is no lens at all", async (key) => {
    render(<StoryView event={event()} />);
    expect(await screen.findByText(READER_BRIEF)).toBeInTheDocument();

    await userEvent.keyboard(key);

    expect(screen.getByText(READER_BRIEF)).toBeInTheDocument();
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
    await screen.findByText(READER_BRIEF);

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
    await screen.findByText(READER_BRIEF);

    // role=button excludes the desktop tabs, which declare role=tab.
    await userEvent.click(screen.getByRole("button", { name: /Cyber/ }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Sign in to unlock/ })).toBeInTheDocument(),
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
    await screen.findByText(READER_BRIEF);

    await userEvent.click(screen.getByRole("button", { name: /Cyber/ }));

    expect(scrollIntoView).toHaveBeenCalledWith(expect.objectContaining({ behavior: "auto" }));
  });
});

describe("locked lens", () => {
  // Free tier discipline: flipping to a locked lens must not generate a brief.
  // Every signed-out visitor tapping Cyber would otherwise bill an LLM call.
  it("generates no brief for a signed-out reader", async () => {
    render(<StoryView event={event({ lens_briefs: { reader: READER_BRIEF } } as Partial<EventDetail>)} />);
    await screen.findByText(READER_BRIEF);
    fetchBrief.mockClear();

    await userEvent.click(screen.getAllByRole("tab", { name: /Cyber/ })[0]);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Sign in to unlock/ })).toBeInTheDocument(),
    );
    expect(fetchBrief).not.toHaveBeenCalled();
  });
});
