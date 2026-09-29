import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StoryView } from "@/components/StoryView";
import { fetchBrief, fetchQuestions } from "@/lib/api";
import type { BriefResult, EventDetail } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchBrief: vi.fn(async () => null), fetchQuestions: vi.fn(async () => []) };
});
vi.mock("@/lib/watchlist", () => ({ getWatchlist: vi.fn(async () => []), follow: vi.fn(), unfollow: vi.fn() }));
const billing = vi.hoisted(() => ({ fetchPlans: vi.fn(), subscribe: vi.fn() }));
vi.mock("@/lib/billing", async (orig) => ({ ...(await orig<typeof import("@/lib/billing")>()), ...billing }));
const track = vi.hoisted(() => vi.fn());
vi.mock("@/lib/analytics", async (orig) => ({ ...(await orig<typeof import("@/lib/analytics")>()), track }));
const PLANS = { offer: false, offer_ends: null, founding_left: 0, checkout_ready: true, key_id: "rzp_test_x", plans: [{ plan: "plus_monthly", label: "Plus · monthly", amount_paise: 14900, period: "month" }] };
const META = {
  reader: { slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" },
  cyber: { slug: "cyber", short: "Cyber", color: "#06B6D4", bg: "#e0f7fa", tagline: "t" },
  markets: { slug: "markets", short: "Markets", color: "#117A48", bg: "#e0f5ea", tagline: "t" },
};
vi.mock("@/lib/lenses", async () => ({
  ...(await vi.importActual<typeof import("@/lib/lenses")>("@/lib/lenses")),
  useLenses: () => Object.values(META),
  lensMeta: (slug: string) => META[slug as keyof typeof META] ?? META.reader,
}));

// jsdom has no viewport, so every composition renders; the article is the
// one-brief-at-a-time tree these tests are about.
function mobile() {
  const root = document.querySelector("article");
  if (!root) throw new Error("mobile tree not found");
  return within(root as HTMLElement);
}

const READER_BRIEF = "The reader take on this story.";
const CYBER_BRIEF = "The cyber take on this story.";
const MARKETS_BRIEF = "The markets take on this story.";
const SIGNED_IN = JSON.stringify({ token: "t", userId: "u", email: "e@x.dev" });

// As the page receives it: fetched anonymously, so only the Reader brief and
// no lens facts (api/routes/events.py strips them).
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
  lens_briefs: { reader: READER_BRIEF },
  lens_points: {},
  available_lenses: ["reader", "cyber", "markets"],
  coverage: null,
  entities: [],
  sources: [],
  perspectives: [],
  impacts: [],
  claims: [],
} as unknown as EventDetail;

const ok = (lens: string, brief: string | null, over: Partial<BriefResult> = {}) =>
  ({ state: "ok", lens, brief, cached: true, facts: null, ...over }) as BriefResult;

beforeEach(() => {
  localStorage.clear();
  track.mockReset();
  billing.fetchPlans.mockReset().mockResolvedValue(PLANS);
  billing.subscribe.mockReset();
  vi.mocked(fetchBrief).mockReset().mockResolvedValue(null as unknown as BriefResult);
  // jsdom implements no scrollIntoView, and the pinned rail — the one
  // tablist on the page now — calls it on every pick.
  Element.prototype.scrollIntoView = vi.fn();
});

describe("lens flip", () => {
  // REGRESSION (ISSUE-004): a tap on a lens has to flip it — no dead button.
  // Since 2026-09-27 a reader without an account reads it too, against the
  // meter (three a session), so the tap asks the server rather than locking.
  it("flips a signed-out reader to the lens and reads it against the meter", async () => {
    vi.mocked(fetchBrief).mockResolvedValue(ok("cyber", CYBER_BRIEF));
    render(<StoryView event={EVENT} />);
    expect(await mobile().findByText(READER_BRIEF)).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole("tab", { name: /Cyber/ })[0]);

    expect(await mobile().findByText(CYBER_BRIEF)).toBeInTheDocument();
    expect(mobile().queryByText(READER_BRIEF)).not.toBeInTheDocument();
    expect(vi.mocked(fetchBrief)).toHaveBeenCalledWith("e1", "cyber", undefined, false);
  });

  it("shows a signed-out reader past the meter the way in, and Plus beside it", async () => {
    vi.mocked(fetchBrief).mockResolvedValue({ state: "signin_required", used: 3, limit: 3 });
    render(<StoryView event={EVENT} />);
    await userEvent.click(screen.getAllByRole("tab", { name: /Cyber/ })[0]);

    expect(await mobile().findByRole("button", { name: "Sign in to keep reading" })).toBeInTheDocument();
    // The door is the anonymous wall's own, and /plus brings the reader back here (audit 2026-09-29, P1-3).
    expect(mobile().getByRole("link", { name: /Every lens with Plus/ })).toHaveAttribute("href", "/plus?from=lens-signin&next=%2Fstory%2Fe1");
    expect(screen.getAllByRole("tab", { name: /Cyber/ })[0]).toHaveAttribute("aria-selected", "true");
  });

  // The out-of-readings card offered only "Back to the reader view": the one
  // reader Plus is for was given no way to it (audit P0 #6d). Then it sent
  // them off the story to /plus and never back (audit 2026-09-29, P1-2): Plus
  // opens over the story now, and paying opens the lens they were stopped at.
  it("shows a free account past its day's readings Plus in place, and opens the lens once they pay", async () => {
    localStorage.setItem("prism.session.v1", SIGNED_IN);
    vi.mocked(fetchBrief).mockResolvedValue({ state: "limit", used: 10, limit: 10 });
    billing.subscribe.mockResolvedValue({ plan: "plus_monthly", status: "active", entitled: true });
    render(<StoryView event={EVENT} />);
    await userEvent.click(screen.getAllByRole("tab", { name: /Markets/ })[0]);

    expect(await mobile().findByText("You have read 10 of 10 free lens readings today")).toBeInTheDocument();
    expect(mobile().getByRole("button", { name: "Back to the reader view" })).toBeInTheDocument();
    await userEvent.click(mobile().getByRole("button", { name: "Get Plus" }));
    const sheet = screen.getByRole("dialog", { name: "Every lens on this story" });
    expect(sheet).toHaveTextContent("10 of 10 today");
    expect(within(sheet).getByRole("link", { name: "All plans →" })).toHaveAttribute("href", "/plus?from=lens-limit&next=%2Fstory%2Fe1");

    vi.mocked(fetchBrief).mockResolvedValue(ok("markets", MARKETS_BRIEF));
    await userEvent.click(await within(sheet).findByRole("button", { name: /Get Plus · ₹149 a month/ }));
    expect(await within(sheet).findByRole("status")).toHaveTextContent("The Markets read is open.");
    expect(await mobile().findByText(MARKETS_BRIEF)).toBeInTheDocument();
    expect(mobile().queryByText(/free lens readings today/)).not.toBeInTheDocument();
  });

  // The count read the gate as it stood BEFORE the server answered, so the
  // first locked tap was counted as an open (audit 2026-09-29, §2.5 bug 1).
  it("counts a lens from the server's answer, once per lens on the page", async () => {
    vi.mocked(fetchBrief).mockResolvedValue({ state: "signin_required", used: 3, limit: 3 });
    render(<StoryView event={EVENT} />);
    await userEvent.click(screen.getAllByRole("tab", { name: /Markets/ })[0]);
    await mobile().findByRole("button", { name: "Sign in to keep reading" });
    await userEvent.click(screen.getAllByRole("tab", { name: /Reader/ })[0]);
    await userEvent.click(screen.getAllByRole("tab", { name: /Markets/ })[0]);
    await waitFor(() => expect(vi.mocked(fetchBrief)).toHaveBeenCalledTimes(2));
    await userEvent.click(screen.getAllByRole("tab", { name: /Reader/ })[0]);

    const lensCounts = track.mock.calls.filter(([e]) => e === "Lens").map(([, p]) => p);
    expect(lensCounts).toEqual([{ lens: "markets", locked: true }, { lens: "reader", locked: false }]);
    expect(track).toHaveBeenCalledWith("Subscribe", { stage: "prompt", from: "lens-signin" });
    expect(track.mock.calls.filter(([e]) => e === "Subscribe")).toHaveLength(1);
  });

  // The lens facts (tickers, catalyst, CVSS…) were shown to nobody: the page is
  // fetched anonymously and the record strips them. They come with /brief now,
  // and they print while the prose is still being written.
  it("prints the facts at once and holds only the prose behind the skeleton", async () => {
    localStorage.setItem("prism.session.v1", SIGNED_IN);
    const facts = { tickers: ["RELIANCE"], catalyst: "earnings" };
    let write!: (r: BriefResult) => void;
    vi.mocked(fetchBrief)
      .mockResolvedValueOnce(ok("markets", null, { pending: true, facts }))
      .mockImplementationOnce(() => new Promise((resolve) => (write = resolve)));
    render(<StoryView event={EVENT} />);
    await userEvent.click(screen.getAllByRole("tab", { name: /Markets/ })[0]);

    expect(await mobile().findByText("RELIANCE")).toBeInTheDocument();
    expect(mobile().getByText(/Writing the Markets read/)).toBeInTheDocument();
    expect(vi.mocked(fetchBrief)).toHaveBeenLastCalledWith("e1", "markets", "t", true);

    write(ok("markets", MARKETS_BRIEF, { facts, cached: false }));
    expect(await mobile().findByText(MARKETS_BRIEF)).toBeInTheDocument();
    expect(mobile().getByText("RELIANCE")).toBeInTheDocument();
    expect(mobile().queryByText(/Writing the Markets read/)).not.toBeInTheDocument();
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
    localStorage.setItem("prism.session.v1", SIGNED_IN);
    vi.mocked(fetchQuestions).mockClear();
    render(<StoryView event={EVENT} />);
    await waitFor(() =>
      expect(vi.mocked(fetchQuestions)).toHaveBeenCalledWith(EVENT.id, expect.anything(), "t"),
    );
  });

  // The guard still has to do its original job: a shared link opened by a
  // signed-out visitor whose profile says "cyber" must not land on the sign-in
  // wall as the whole story when the meter says no.
  it("still snaps back a profile-restored lens the meter refuses", async () => {
    localStorage.setItem("prism.profile.v1", JSON.stringify({ lens: "cyber" }));
    vi.mocked(fetchBrief).mockResolvedValue({ state: "signin_required", used: 3, limit: 3 });
    render(<StoryView event={EVENT} />);
    await waitFor(() => expect(vi.mocked(fetchBrief)).toHaveBeenCalled());
    expect(await mobile().findByText(READER_BRIEF)).toBeInTheDocument();
    expect(mobile().queryByRole("button", { name: "Sign in to keep reading" })).not.toBeInTheDocument();
    // Nobody tapped: a lens the profile asked for is not a reader opening one.
    expect(track).not.toHaveBeenCalledWith("Lens", expect.anything());
  });
});

describe("lens flip — signing out mid-read", () => {
  // useSession subscribes to the `storage` event, so signing out in ANOTHER tab
  // flips this one to signed-out on a mounted story. A lens already opened here
  // stays readable: no wall appears over what the reader was reading.
  it("keeps a lens already opened when the session disappears from another tab", async () => {
    localStorage.setItem("prism.session.v1", SIGNED_IN);
    vi.mocked(fetchBrief).mockResolvedValue(ok("cyber", CYBER_BRIEF));
    render(<StoryView event={EVENT} />);
    await userEvent.click(screen.getAllByRole("tab", { name: /Cyber/ })[0]);
    expect(await mobile().findByText(CYBER_BRIEF)).toBeInTheDocument();

    localStorage.removeItem("prism.session.v1");
    window.dispatchEvent(new StorageEvent("storage", { key: "prism.session.v1" }));

    await waitFor(() => expect(mobile().getByText(CYBER_BRIEF)).toBeInTheDocument());
    expect(mobile().queryByRole("button", { name: "Sign in to keep reading" })).not.toBeInTheDocument();
  });
});
