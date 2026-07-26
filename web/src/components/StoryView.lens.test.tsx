import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StoryView } from "@/components/StoryView";
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
  thread: null,
  related: [],
  story: { developments: [] },
  sources: [],
  perspectives: [],
  impacts: [],
} as unknown as EventDetail;

beforeEach(() => {
  localStorage.clear();
});

describe("lens flip", () => {
  // REGRESSION (ISSUE-004): a guard effect snapped any locked lens back to
  // "reader", and it watched `lens` — so it also caught the reader deliberately
  // TAPPING a pro lens, reverting it in the same commit. Every lens control on
  // the page (tabs, pinned rail, keyboard 1/2/3) was a dead button for a
  // signed-out reader: no re-typeset, no unlock prompt, nothing.
  it("flips a signed-out reader to the locked lens so they see the unlock prompt", async () => {
    render(<StoryView event={EVENT} />);
    expect(await screen.findByText(READER_BRIEF)).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole("tab", { name: /Cyber/ })[0]);

    await waitFor(() => expect(screen.queryByText(READER_BRIEF)).not.toBeInTheDocument());
    // Locked: the flip happens, but the brief stays behind the sign-in prompt.
    expect(screen.queryByText(CYBER_BRIEF)).not.toBeInTheDocument();
    expect(screen.getAllByRole("tab", { name: /Cyber/ })[0]).toHaveAttribute("aria-selected", "true");
  });

  it("swaps the brief for a signed-in reader", async () => {
    localStorage.setItem(
      "prism.session.v1",
      JSON.stringify({ token: "t", userId: "u", email: "e@x.dev" }),
    );
    render(<StoryView event={EVENT} />);
    expect(await screen.findByText(READER_BRIEF)).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole("tab", { name: /Cyber/ })[0]);

    expect(await screen.findByText(CYBER_BRIEF)).toBeInTheDocument();
    expect(screen.queryByText(READER_BRIEF)).not.toBeInTheDocument();
  });

  // The guard still has to do its original job: a shared link opened by a
  // signed-out visitor whose profile says "cyber" must not land on the sign-in
  // wall as the whole story.
  it("still snaps back a profile-restored locked lens the reader did not pick", async () => {
    localStorage.setItem("prism.profile.v1", JSON.stringify({ lens: "cyber" }));
    render(<StoryView event={EVENT} />);
    expect(await screen.findByText(READER_BRIEF)).toBeInTheDocument();
  });
});
