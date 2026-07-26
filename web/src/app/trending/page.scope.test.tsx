import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TrendingPage from "@/app/trending/page";

const fetchTrending = vi.hoisted(() => vi.fn());
const loadProfile = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({ fetchTrending }));
vi.mock("@/lib/profile", () => ({ loadProfile }));
// @/lib/scope is deliberately NOT mocked: the point is the real persisted value.

beforeEach(() => {
  fetchTrending.mockReset().mockResolvedValue([]);
  loadProfile.mockReset().mockReturnValue(null);
  // The suite-wide afterEach clears sessionStorage only, and this page now READS
  // localStorage — without this, a scope saved by an earlier test decides this one.
  localStorage.clear();
});

describe("Trending — the scope the reader chose elsewhere", () => {
  // The scope sheet promises "Applies everywhere". Trending has no "all" tier,
  // so the world-wide choice has to land on its closest equivalent.
  it("opens on National when the reader picked World on the Feed", async () => {
    localStorage.setItem("parse.scope.v1", "all");
    loadProfile.mockReturnValue({ state: "IN-KL" });

    render(<TrendingPage />);

    expect(await screen.findByRole("button", { name: /National/ })).toBeInTheDocument();
    await waitFor(() => expect(fetchTrending).toHaveBeenCalled());
    for (const call of fetchTrending.mock.calls) expect(call[0].state).toBeNull();
  });

  // REGRESSION (ISSUE-001): scope and profile are separate keys, so they drift.
  // A saved "region" with no state left the chip claiming "Your state" over an
  // unfiltered list, and the sheet's own option was disabled so the reader
  // could not correct it.
  it("does not claim Your state when the reader has no state", async () => {
    localStorage.setItem("parse.scope.v1", "region");

    render(<TrendingPage />);

    expect(await screen.findByRole("button", { name: /National/ })).toBeInTheDocument();
    expect(screen.queryByText(/Your state/)).not.toBeInTheDocument();
  });

  // The other half of the round-trip the sheet promises: a reader who picked
  // their state on the Feed must land on it here, chip AND query. Trending is
  // the surface where "region" is a real filter (its own default is National),
  // so a dropped saved scope shows up as the wrong list, not just a wrong label.
  it("opens on the reader's state when that is what they saved", async () => {
    localStorage.setItem("parse.scope.v1", "region");
    loadProfile.mockReturnValue({ state: "IN-KL" });

    render(<TrendingPage />);

    expect(await screen.findByRole("button", { name: /Kerala/ })).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchTrending).toHaveBeenCalledWith(expect.objectContaining({ state: "IN-KL" })),
    );
  });

  it("persists the pick so the Feed agrees on the next visit", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<TrendingPage />);

    await userEvent.click(await screen.findByRole("button", { name: /Kerala/ }));
    await userEvent.click(await screen.findByRole("button", { name: "National" }));

    expect(localStorage.getItem("parse.scope.v1")).toBe("world");
  });
});
