import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FeedPage from "@/app/feed/page";
import type { FeedItem } from "@/lib/api";

const fetchFeed = vi.hoisted(() => vi.fn());
const fetchDigest = vi.hoisted(() => vi.fn());
const fetchTrending = vi.hoisted(() => vi.fn());
const fetchRegions = vi.hoisted(() => vi.fn());
const loadProfile = vi.hoisted(() => vi.fn());
const useSession = vi.hoisted(() => vi.fn());
const watchlistEvents = vi.hoisted(() => vi.fn());
const useTaxonomy = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", () => ({ fetchFeed, fetchDigest, fetchTrending, fetchRegions }));
vi.mock("@/lib/profile", () => ({ loadProfile }));
vi.mock("@/lib/session", () => ({ useSession }));
vi.mock("@/lib/watchlist", () => ({ watchlistEvents }));
vi.mock("@/components/ProfileEditor", () => ({ useTaxonomy }));
// @/lib/scope stays real: the whole point is what happens when it CAN'T persist.

const ITEM = {
  id: "e1",
  title: "A story that came back from the cache",
  headline_lang: null,
  available_languages: [],
  summary: "s",
  sector: "politics",
  subsector: null,
  regions: [],
  image_url: null,
  is_regional: true, // survives the region filter, so it renders under either scope
  coverage: null,
  event_type: null,
  source_count: 4,
  cvss_score: null,
  cvss_severity: null,
  kev_listed: false,
  cve_ids: [],
  tickers: [],
  catalyst: null,
  price_impact_direction: null,
  last_updated_at: "2026-07-25T12:00:00Z",
  score: 1,
} as FeedItem;

beforeEach(() => {
  // Resolving, unlike page.test.tsx: an actual feed is what fills the module
  // cache, and the cache is what this file is about.
  fetchFeed.mockReset().mockResolvedValue([ITEM]);
  fetchDigest.mockReset().mockResolvedValue(null);
  fetchTrending.mockReset().mockResolvedValue([]);
  fetchRegions.mockReset().mockResolvedValue([{ code: "IN-KL", name: "Kerala" }]);
  loadProfile.mockReset().mockReturnValue({ state: "IN-KL" });
  useSession.mockReset().mockReturnValue(null);
  watchlistEvents.mockReset().mockResolvedValue([]);
  useTaxonomy.mockReset().mockReturnValue([{ slug: "politics", name: "Politics", subsectors: [] }]);
});

afterEach(() => vi.unstubAllGlobals());

describe("Feed — the module cache on a return navigation", () => {
  // The reader is in an in-app webview (WhatsApp, Instagram): localStorage
  // throws, so their scope pick cannot be written down. Within the session the
  // module cache is the only memory the Feed has — and the mount effect's
  // "no saved scope, so default to their state" fallback would overwrite it on
  // every return from a story, silently dragging the reader back to Kerala
  // after they asked for All. `restoredCache` is what stops that.
  it("keeps a pick that could not be persisted when the reader comes back", async () => {
    const boom = () => {
      throw new DOMException("denied", "SecurityError");
    };
    vi.stubGlobal("localStorage", { getItem: boom, setItem: boom, clear: () => {} });

    const first = render(<FeedPage />);
    // Their state is the default, since nothing is saved and they have one.
    await screen.findByRole("button", { name: /Kerala/ });
    // Wait for the feed itself: the cache is only written once items land.
    await screen.findByText(ITEM.title);

    await userEvent.click(screen.getByRole("button", { name: /Kerala/ }));
    await userEvent.click(await screen.findByRole("button", { name: "All" }));
    await waitFor(() => expect(screen.getByRole("button", { name: /All/ })).toBeInTheDocument());

    first.unmount(); // tap a story…
    render(<FeedPage />); // …and come back

    expect(await screen.findByRole("button", { name: /All/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Kerala/ })).not.toBeInTheDocument();
    // Restored from the module cache, so the reader's place is there immediately.
    expect(screen.getByText(ITEM.title)).toBeInTheDocument();
  });
});
