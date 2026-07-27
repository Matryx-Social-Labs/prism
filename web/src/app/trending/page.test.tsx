import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TrendingPage from "@/app/trending/page";
import type { TrendingStory } from "@/lib/api";

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
    expect(await screen.findByRole("button", { name: /National/ })).toBeInTheDocument();
    await waitFor(() => expect(fetchTrending).toHaveBeenCalled());
    // No state => never request a region-scoped list.
    for (const call of fetchTrending.mock.calls) expect(call[0].state).toBeNull();
  });

  it("opens on the reader's own state when they have one", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<TrendingPage />);
    // The chip specifically: the story fixture headline also says "Kerala".
    expect(await screen.findByRole("button", { name: /Kerala/ })).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchTrending).toHaveBeenCalledWith(expect.objectContaining({ state: "IN-KL" }))
    );
  });

  it("shows the raw code for a state it has no name for", async () => {
    // Regression risk: stateLabel hardcodes seven states, so an eighth reader
    // sees "IN-GJ". Pinning current behavior so the fix is visible when it lands.
    loadProfile.mockReturnValue({ state: "IN-GJ" });
    render(<TrendingPage />);
    expect(await screen.findByText(/IN-GJ/)).toBeInTheDocument();
  });

  it("switches to National from the scope sheet", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<TrendingPage />);
    await screen.findByRole("button", { name: /Kerala/ });

    await userEvent.click(screen.getByRole("button", { name: /Kerala/ }));
    await userEvent.click(await screen.findByRole("button", { name: "National" }));

    await waitFor(() =>
      expect(fetchTrending).toHaveBeenCalledWith(expect.objectContaining({ state: null }))
    );
  });
});

describe("Trending — sector chips", () => {
  it("offers only filters that can actually return a story", async () => {
    render(<TrendingPage />);
    await screen.findByText("All sectors");
    // Cyber is excluded from trending upstream, so a Cyber chip is a dead end.
    expect(screen.queryByRole("button", { name: "Cyber" })).not.toBeInTheDocument();
  });

  it("queries the taxonomy sector slug, not the subsector, for Markets", async () => {
    render(<TrendingPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Markets" }));
    // "markets" is a subsector of finance; the API filters on sector.
    await waitFor(() =>
      expect(fetchTrending).toHaveBeenCalledWith(expect.objectContaining({ sector: "finance" }))
    );
  });

  it("clears the filter with All sectors", async () => {
    render(<TrendingPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Politics" }));
    await waitFor(() =>
      expect(fetchTrending).toHaveBeenCalledWith(expect.objectContaining({ sector: "politics" }))
    );
    await userEvent.click(screen.getByRole("button", { name: "All sectors" }));
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
    const link = await screen.findByRole("link", { name: /CPI\(M\) · Pinarayi Vijayan/ });
    expect(link).toHaveAttribute("href", "/trending/kerala-power");
    expect(link).not.toHaveTextContent("Kerala power crisis deepens");
  });

  it("falls back to the hero headline when a storyline has no label", async () => {
    fetchTrending.mockResolvedValue([story({ label: null as unknown as string })]);
    render(<TrendingPage />);
    expect(await screen.findByText(/Kerala power crisis deepens/)).toBeInTheDocument();
  });

  it("renders an empty state rather than a dead screen", async () => {
    fetchTrending.mockResolvedValue([]);
    render(<TrendingPage />);
    await waitFor(() => expect(screen.queryByRole("link")).not.toBeInTheDocument());
  });

  it("does not crash when the API is down", async () => {
    fetchTrending.mockRejectedValue(new Error("unreachable"));
    render(<TrendingPage />);
    expect(await screen.findByText("Trending")).toBeInTheDocument();
  });
});

describe("Trending — state names", () => {
  // REGRESSION: this page carried a hand-written map of seven Indian states, so
  // a reader in any of the other ~29 saw the raw ISO code in the scope chip —
  // while the Feed, one tab away, resolved the same code from /api/v1/regions.
  it("names a state that the old seven-state map never covered", async () => {
    loadProfile.mockReturnValue({ state: "IN-BR" });
    render(<TrendingPage />);
    expect(await screen.findByRole("button", { name: /Bihar/ })).toBeInTheDocument();
  });

  it("falls back to the code when the API doesn't know it", async () => {
    loadProfile.mockReturnValue({ state: "IN-XX" });
    render(<TrendingPage />);
    expect(await screen.findByRole("button", { name: /IN-XX/ })).toBeInTheDocument();
  });
});
