import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import PulsePage from "@/app/pulse/page";

const fetchDigest = vi.hoisted(() => vi.fn());
const useSession = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({ fetchDigest }));
vi.mock("@/lib/session", () => ({ useSession }));

const DIGEST = { headline: "Rupee steadies", narrative: "Para one.\n\nPara two.", movers: [{ ticker: "RELIANCE", note: "bid on refining" }], event_ids: ["a", "b"], generated_at: "2026-09-16T04:00:00Z" };

beforeEach(() => {
  fetchDigest.mockReset().mockResolvedValue(DIGEST);
  useSession.mockReset().mockReturnValue(null);
});

describe("Market Pulse — the chart supplement", () => {
  it("prints the digest, counts the stories behind it, and sends a ticker to search for a reader with no watchlist", async () => {
    render(<PulsePage />);
    expect(await screen.findByRole("heading", { level: 1, name: "Rupee steadies" })).toBeInTheDocument();
    expect(screen.getByText(/synthesized across 2 stories/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "RELIANCE" })).toHaveAttribute("href", "/search?q=RELIANCE");
  });

  it("sends a ticker to that ticker's watchlist rows when the reader is signed in", async () => {
    useSession.mockReturnValue({ token: "t", userId: "u", email: "a@b.c" });
    render(<PulsePage />);
    expect(await screen.findByRole("link", { name: "RELIANCE" })).toHaveAttribute("href", "/watchlist?ticker=RELIANCE");
  });

  it("says so when there is no pulse", async () => {
    fetchDigest.mockResolvedValue(null);
    render(<PulsePage />);
    expect(await screen.findByText(/isn’t available right now/)).toBeInTheDocument();
  });
});

describe("the pulse shows the record under the reading", () => {
  it("lists the stories the digest was written from as chart rows", async () => {
    const { fetchDigest } = await import("@/lib/api");
    (fetchDigest as unknown as { mockResolvedValueOnce: (v: unknown) => void }).mockResolvedValueOnce({
      headline: "Markets hold", narrative: "Calm.", movers: [], event_ids: ["e1"], generated_at: null,
      stories: [{ id: "e1", title: "RBI holds the repo rate", headline_lang: "en", available_languages: ["en"], summary: null, sector: "finance", subsector: null, regions: ["IN"], image_url: null, is_regional: false, source_count: 12, score: 1, cyber: null, finance: null, latest_published_at: null, last_updated_at: "2026-09-17T06:00:00Z", occurred_at: null, coverage: null, headlines: [] }],
    });
    const { default: Page } = await import("@/app/pulse/page");
    render(<Page />);
    expect(await screen.findByText("Written from")).toBeInTheDocument();
    expect(screen.getByText("RBI holds the repo rate")).toBeInTheDocument();
  });
});
