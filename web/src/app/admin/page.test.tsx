import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AdminOverview from "@/app/admin/page";

const fetchMetrics = vi.hoisted(() => vi.fn());
const fetchLabellers = vi.hoisted(() => vi.fn());
const fetchBatches = vi.hoisted(() => vi.fn());
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));

vi.mock("@/components/admin/AdminShell", async (orig) => ({
  ...(await orig<typeof import("@/components/admin/AdminShell")>()),
  useAdmin: () => ADMIN,
}));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchMetrics, fetchLabellers, fetchBatches }));

const metrics = (days: number) => ({
  range: { days, start: "2031-01-04", end: "2031-01-31", prev_start: "2030-12-07", prev_end: "2031-01-03", tz: "Asia/Kolkata" },
  counting_since: { usage: "2031-01-30", active: null },
  sections: [
    { key: "visits", title: "Visits", breakdowns: [],
      rows: [{ key: "views", label: "Page views", current: 7, previous: null, series: null, unit: "count", source: "usage_daily", note: null }] },
  ],
});

beforeEach(() => {
  fetchMetrics.mockReset().mockImplementation(async (_s: unknown, days: number) => metrics(days));
  fetchLabellers.mockReset().mockResolvedValue({ labellers: [{ status: "applied" }, { status: "active" }], board: [], languages: [] });
  fetchBatches.mockReset().mockResolvedValue({ batches: [{ purpose: "practice", open: false, gated: 0, tasks: 8 }, { purpose: "work", open: true, gated: 150, tasks: 150 }] });
});

describe("the overview", () => {
  it("says what is waiting on a founder, and links to it", async () => {
    render(<AdminOverview />);
    const apps = await screen.findByRole("link", { name: /1 applications to read/ });
    expect(apps).toHaveAttribute("href", "/admin/labellers");
    expect(screen.getByRole("link", { name: /1 practice rounds or tests not published/ })).toBeInTheDocument();
    // A fully gated work batch is not waiting on anyone.
    expect(screen.queryByText(/without a language gate/)).not.toBeInTheDocument();
  });

  it("shows the period and when counting began, and re-reads on a new period", async () => {
    render(<AdminOverview />);
    expect(await screen.findByText(/VISITS COUNTED SINCE 30 JAN/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Visits" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "90 days" }));
    expect(fetchMetrics).toHaveBeenLastCalledWith(ADMIN.session, 90);
    expect(screen.getByRole("tab", { name: "90 days" })).toHaveAttribute("aria-selected", "true");
  });

  it("leads with the headline numbers and puts supply, counted longest, first", async () => {
    fetchMetrics.mockResolvedValue({
      ...metrics(28),
      sections: [
        { key: "visits", title: "Visits", breakdowns: [],
          rows: [{ key: "visitor_days", label: "Visitor-days", current: null, previous: null, series: null, unit: "count", source: "usage_daily", note: null }] },
        { key: "supply", title: "Supply", breakdowns: [],
          rows: [{ key: "reports", label: "Reports fetched", current: 1284, previous: 1000, series: null, unit: "count", source: "raw_items", note: null }] },
      ],
    });
    render(<AdminOverview />);
    const tile = (await screen.findAllByRole("heading", { name: "Reports fetched" }))[0].closest(".admin-panel")!;
    expect(tile).toHaveTextContent("1,284");
    expect(tile).toHaveTextContent("+28%");
    // Uncounted is a dash, never a zero, in the headline as everywhere.
    expect(screen.getAllByRole("heading", { name: "Visitor-days" })[0].closest(".admin-panel")).toHaveTextContent("Not counted yet");
    const sections = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(sections.indexOf("Supply")).toBeLessThan(sections.indexOf("Visits"));
  });

  it("never says nothing is waiting when it could not look", async () => {
    fetchBatches.mockRejectedValue(new Error("offline"));
    render(<AdminOverview />);
    expect(await screen.findByText(/Could not check what is waiting/)).toBeInTheDocument();
    expect(screen.queryByText("Nothing is waiting on you.")).not.toBeInTheDocument();
  });

  it("says plainly when nothing is waiting", async () => {
    fetchLabellers.mockResolvedValue({ labellers: [], board: [], languages: [] });
    fetchBatches.mockResolvedValue({ batches: [] });
    render(<AdminOverview />);
    expect(await screen.findByText("Nothing is waiting on you.")).toBeInTheDocument();
  });
});
