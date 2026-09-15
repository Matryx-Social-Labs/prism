import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StoryView } from "@/components/StoryView";
import { fetchQuestions } from "@/lib/api";
import type { EventDetail } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchBrief: vi.fn(async () => null), fetchQuestions: vi.fn(async () => []) };
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


// The desktop composition shows ALL three lens openings at once (the lens board),
// so "the reader brief is gone" is only true of the mobile tree — which is the
// one-brief-at-a-time composition these tests are about. Scope to it, rather than
// weakening the assertion to "appears somewhere".
function mobile() {
  const root = document.querySelector(".lg\\:hidden");
  if (!root) throw new Error("mobile tree not found");
  return within(root as HTMLElement);
}

const READER_BRIEF = "The reader take on this story.";
const CYBER_BRIEF = "The cyber take on this story.";

const EVENT = {
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
} as unknown as EventDetail;

beforeEach(() => {
  localStorage.clear();
});

// jsdom has no viewport, so BOTH the desktop composition and the mobile tree
// render — hence findAllByText/queryAllByText throughout. In a browser exactly
// one of them is displayed.
describe("lens flip", () => {
  // REGRESSION (ISSUE-004): a guard effect snapped any locked lens back to
  // "reader", and it watched `lens` — so it also caught the reader deliberately
  // TAPPING a pro lens, reverting it in the same commit. Every lens control on
  // the page (tabs, pinned rail, keyboard 1/2/3) was a dead button for a
  // signed-out reader: no re-typeset, no unlock prompt, nothing.
  it("flips a signed-out reader to the locked lens so they see the unlock prompt", async () => {
    render(<StoryView event={EVENT} />);
    expect(await mobile().findByText(READER_BRIEF)).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole("tab", { name: /Cyber/ })[0]);

    await waitFor(() => expect(mobile().queryByText(READER_BRIEF)).not.toBeInTheDocument());
    // Locked: the flip happens, but the brief stays behind the sign-in prompt.
    expect(mobile().queryByText(CYBER_BRIEF)).not.toBeInTheDocument();
    expect(screen.getAllByRole("tab", { name: /Cyber/ })[0]).toHaveAttribute("aria-selected", "true");
  });

  it("swaps the brief for a signed-in reader", async () => {
    localStorage.setItem(
      "prism.session.v1",
      JSON.stringify({ token: "t", userId: "u", email: "e@x.dev" }),
    );
    render(<StoryView event={EVENT} />);
    expect(await mobile().findByText(READER_BRIEF)).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole("tab", { name: /Cyber/ })[0]);

    expect(await mobile().findByText(CYBER_BRIEF)).toBeInTheDocument();
    expect(mobile().queryByText(READER_BRIEF)).not.toBeInTheDocument();
  });

  // The token has to reach /questions too, not only /brief. One suggested
  // question is derived from story data — the cyber lens swaps in the
  // exploited-in-the-wild phrasing when the CVE is KEV-listed — and the server
  // now serves it only to a reader who unlocked that lens. Fetching it
  // unauthenticated would hand the paying reader the free copy, so plugging the
  // leak would have quietly removed what they are paying for.
  //
  // mockClear first: beforeEach only clears localStorage, so without it this
  // would pass on the signed-in call left behind by the test above.
  it("sends the session token when it asks for suggested questions", async () => {
    localStorage.setItem(
      "prism.session.v1",
      JSON.stringify({ token: "t", userId: "u", email: "e@x.dev" }),
    );
    vi.mocked(fetchQuestions).mockClear();
    render(<StoryView event={EVENT} />);
    await waitFor(() =>
      expect(vi.mocked(fetchQuestions)).toHaveBeenCalledWith(EVENT.id, expect.anything(), "t"),
    );
  });

  // The guard still has to do its original job: a shared link opened by a
  // signed-out visitor whose profile says "cyber" must not land on the sign-in
  // wall as the whole story.
  it("still snaps back a profile-restored locked lens the reader did not pick", async () => {
    localStorage.setItem("prism.profile.v1", JSON.stringify({ lens: "cyber" }));
    render(<StoryView event={EVENT} />);
    expect(await mobile().findByText(READER_BRIEF)).toBeInTheDocument();
  });
});

describe("lens flip — signing out mid-read", () => {
  // REVIEW (maintainability + design, multi-specialist): readerPicked was set
  // once and never cleared, so it meant "touched a lens control at some point",
  // not "the current lens is a deliberate pick". useSession subscribes to the
  // `storage` event, so signing out in ANOTHER tab flips this one to signed-out
  // on a mounted story — and the stale ref left that reader parked on a locked
  // lens with the sign-in wall as the whole story, the exact state the guard
  // exists to prevent.
  it("snaps back to reader when the session disappears from another tab", async () => {
    localStorage.setItem(
      "prism.session.v1",
      JSON.stringify({ token: "t", userId: "u", email: "e@x.dev" }),
    );
    render(<StoryView event={EVENT} />);
    await userEvent.click(screen.getAllByRole("tab", { name: /Cyber/ })[0]);
    expect(await mobile().findByText(CYBER_BRIEF)).toBeInTheDocument();

    // Another tab signs out: the key goes away and `storage` fires.
    localStorage.removeItem("prism.session.v1");
    window.dispatchEvent(new StorageEvent("storage", { key: "prism.session.v1" }));

    expect(await mobile().findByText(READER_BRIEF)).toBeInTheDocument();
    expect(mobile().queryByText(CYBER_BRIEF)).not.toBeInTheDocument();
  });
});
