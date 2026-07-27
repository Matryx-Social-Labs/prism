import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TrendingPage from "@/app/trending/page";
import type { TrendingStory } from "@/lib/api";

// jsdom has no viewport, so BOTH trees render: the desktop composition
// (`lg:block`) and the phone's (`lg:hidden`). Every control that exists on both
// matches twice, so queries below say WHICH surface they mean.

/** A desktop tab, inside its labelled group. */
const tab = (group: "Scope" | "Sector", name: string) =>
  within(screen.getByRole("group", { name: group })).getByRole("button", { name });

/** The phone's copy of a control (its chips and sheet options are ungrouped). */
function phone(name: string | RegExp): HTMLElement {
  const el = screen.getAllByRole("button", { name }).find((b) => !b.closest("[role='group']"));
  if (!el) throw new Error(`no phone control named ${name}`);
  return el;
}

const fetchTrending = vi.hoisted(() => vi.fn());
const fetchRegions = vi.hoisted(() => vi.fn());
const loadProfile = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({ fetchTrending, fetchRegions }));
vi.mock("@/lib/profile", () => ({ loadProfile }));

function story(over: Partial<TrendingStory> = {}): TrendingStory {
  return {
    slug: "kerala-power",
    label: "CPI(M) · Pinarayi Vijayan",
    cast: ["CPI(M)", "Pinarayi Vijayan"],
    source_count: 4,
    velocity: 3,
    developments: 5,
    sector: "politics",
    hero_title: "Kerala power crisis deepens",
    hero_image: null,
    ...over,
  };
}

beforeEach(() => {
  // Trending resolves state names from /api/v1/regions now, like the Feed,
  // instead of a hand-written seven-state map.
  fetchRegions.mockReset().mockResolvedValue([
    { code: "IN-KL", name: "Kerala" },
    { code: "IN-KA", name: "Karnataka" },
    { code: "IN-BR", name: "Bihar" },
  ]);
  fetchTrending.mockReset().mockResolvedValue([story()]);
  loadProfile.mockReset().mockReturnValue(null);
});

describe("Trending — scope", () => {
  it("defaults to National with no saved state", async () => {
    render(<TrendingPage />);
    // The phone's chip carries ◉ and ▾; the desktop tab is named "National" flat.
    expect(await screen.findByRole("button", { name: /◉ National/ })).toBeInTheDocument();
    expect(tab("Scope", "National")).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(fetchTrending).toHaveBeenCalled());
    // No state => never request a region-scoped list.
    for (const call of fetchTrending.mock.calls) expect(call[0].state).toBeNull();
  });

  it("opens on the reader's own state when they have one", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<TrendingPage />);
    // The chip specifically: the story fixture headline also says "Kerala".
    expect(await screen.findByRole("button", { name: /◉ Kerala/ })).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchTrending).toHaveBeenCalledWith(expect.objectContaining({ state: "IN-KL" }))
    );
  });

  it("shows the raw code for a state it has no name for", async () => {
    // Regression risk: stateLabel hardcodes seven states, so an eighth reader
    // sees "IN-GJ". Pinning current behavior so the fix is visible when it lands.
    loadProfile.mockReturnValue({ state: "IN-GJ" });
    render(<TrendingPage />);
    expect(await screen.findByRole("button", { name: /◉ IN-GJ/ })).toBeInTheDocument();
  });

  it("switches to National from the scope sheet", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<TrendingPage />);
    await screen.findByRole("button", { name: /◉ Kerala/ });

    await userEvent.click(phone(/◉ Kerala/));
    // The sheet's option, not the desktop tab of the same name.
    await userEvent.click(phone("National"));

    await waitFor(() =>
      expect(fetchTrending).toHaveBeenCalledWith(expect.objectContaining({ state: null }))
    );
  });
});

describe("Trending — sector chips", () => {
  it("offers only filters that can actually return a story", async () => {
    render(<TrendingPage />);
    await screen.findAllByText("All sectors");
    // Cyber is excluded from trending upstream, so a Cyber chip is a dead end.
    expect(screen.queryByRole("button", { name: "Cyber" })).not.toBeInTheDocument();
  });

  it("queries the taxonomy sector slug, not the subsector, for Markets", async () => {
    render(<TrendingPage />);
    await screen.findAllByText("All sectors");
    await userEvent.click(phone("Markets"));
    // "markets" is a subsector of finance; the API filters on sector.
    await waitFor(() =>
      expect(fetchTrending).toHaveBeenCalledWith(expect.objectContaining({ sector: "finance" }))
    );
  });

  it("clears the filter with All sectors", async () => {
    render(<TrendingPage />);
    await screen.findAllByText("All sectors");
    await userEvent.click(phone("Politics"));
    await waitFor(() =>
      expect(fetchTrending).toHaveBeenCalledWith(expect.objectContaining({ sector: "politics" }))
    );
    await userEvent.click(phone("All sectors"));
    await waitFor(() =>
      expect(fetchTrending).toHaveBeenCalledWith(expect.objectContaining({ sector: null }))
    );
  });
});

describe("Trending — the list", () => {
  // The row names the STORYLINE, not one member's headline. `label` is the cast
  // we generated for the cluster, and it is what the story page it opens shows —
  // leading with hero_title meant the list and the page disagreed about what the
  // story was even called.
  it("leads with the storyline name and links to the story", async () => {
    render(<TrendingPage />);
    // Both surfaces name the row, and both have to name it the same thing.
    const links = await screen.findAllByRole("link", { name: /CPI\(M\) · Pinarayi Vijayan/ });
    expect(links).toHaveLength(2);
    for (const link of links) {
      expect(link).toHaveAttribute("href", "/trending/kerala-power");
      expect(link).not.toHaveTextContent("Kerala power crisis deepens");
    }
  });

  it("falls back to the hero headline when a storyline has no label", async () => {
    fetchTrending.mockResolvedValue([story({ label: null as unknown as string })]);
    render(<TrendingPage />);
    expect(await screen.findAllByText(/Kerala power crisis deepens/)).toHaveLength(2);
  });

  it("renders an empty state rather than a dead screen", async () => {
    fetchTrending.mockResolvedValue([]);
    render(<TrendingPage />);
    await waitFor(() => expect(screen.queryByRole("link")).not.toBeInTheDocument());
  });

  it("does not crash when the API is down", async () => {
    fetchTrending.mockRejectedValue(new Error("unreachable"));
    render(<TrendingPage />);
    expect(await screen.findAllByText("Trending")).toHaveLength(2);
  });
});

describe("Trending — the desktop ledger", () => {
  // Only the desktop composition renders these, so no getAllBy* is needed.
  it("names the storyline AND shows the headline it is running under", async () => {
    render(<TrendingPage />);
    // The phone shows one or the other; the extra desktop width buys both at once.
    expect(await screen.findByText("Kerala power crisis deepens")).toBeInTheDocument();
  });

  it("prints the counted evidence — sources, updates — beside the row", async () => {
    render(<TrendingPage />);
    expect(await screen.findByText("4 sources")).toBeInTheDocument();
    expect(screen.getByText("5 updates")).toBeInTheDocument();
  });

  it("offers no state tab to a reader who has no state", async () => {
    render(<TrendingPage />);
    await screen.findAllByText("All sectors");
    // The phone's sheet disables that option for the same reason: a scope the
    // reader cannot use, on a page whose whole job is scoping.
    expect(within(screen.getByRole("group", { name: "Scope" })).getAllByRole("button")).toHaveLength(1);
  });

  it("scopes the list from the desktop tabs, with no sheet in the way", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<TrendingPage />);
    await waitFor(() => expect(tab("Scope", "Kerala")).toHaveAttribute("aria-pressed", "true"));

    await userEvent.click(tab("Scope", "National"));
    await waitFor(() =>
      expect(fetchTrending).toHaveBeenCalledWith(expect.objectContaining({ state: null })),
    );
  });

  it("filters by sector from the desktop tabs", async () => {
    render(<TrendingPage />);
    await userEvent.click(tab("Sector", "Markets"));
    await waitFor(() =>
      expect(fetchTrending).toHaveBeenCalledWith(expect.objectContaining({ sector: "finance" })),
    );
  });
});

describe("Trending — state names", () => {
  // REGRESSION: this page carried a hand-written map of seven Indian states, so
  // a reader in any of the other ~29 saw the raw ISO code in the scope chip —
  // while the Feed, one tab away, resolved the same code from /api/v1/regions.
  it("names a state that the old seven-state map never covered", async () => {
    loadProfile.mockReturnValue({ state: "IN-BR" });
    render(<TrendingPage />);
    expect(await screen.findByRole("button", { name: /◉ Bihar/ })).toBeInTheDocument();
  });

  it("falls back to the code when the API doesn't know it", async () => {
    loadProfile.mockReturnValue({ state: "IN-XX" });
    render(<TrendingPage />);
    expect(await screen.findByRole("button", { name: /◉ IN-XX/ })).toBeInTheDocument();
  });
});
