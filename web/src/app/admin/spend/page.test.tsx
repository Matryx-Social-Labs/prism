import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import SpendPage from "@/app/admin/spend/page";
import { byStage, runwayDays, type Spend } from "@/lib/admin";

const fetchSpend = vi.hoisted(() => vi.fn());
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({ ...(await orig<typeof import("@/components/admin/AdminShell")>()), useAdmin: () => ADMIN }));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchSpend }));

const stage = (s: string, model: string, calls: number, cost: number, input = 8000 * calls, cached = 0) => ({
  stage: s, model, calls, input_tokens: input, cached_tokens: cached, output_tokens: 650 * calls, cost,
});

const ledger: Spend = {
  balance: { balance: 12.58, at: 1790503235 },
  floor: 5,
  days: [
    { day: "2026-09-28", recorded: true, cost: 7.0, calls: 3100,
      stages: [stage("extract-shared", "gemini-3.1-flash-lite", 2400, 4.2, 19_200_000, 15_360_000), stage("gate-classify", "jev", 700, 2.8)] },
    { day: "2026-09-27", recorded: true, cost: 8.0, calls: 3000,
      stages: [stage("extract-shared", "gemini-3.1-flash-lite", 2000, 6.0), stage("gate-classify", "jev", 1000, 2.0)] },
    { day: "2026-09-26", recorded: false, cost: 0, calls: 0, stages: [] },
  ],
};

beforeEach(() => {
  fetchSpend.mockReset().mockResolvedValue(ledger);
});
afterEach(() => vi.restoreAllMocks());

describe("the spend page", () => {
  it("says a day before the ledger was not recorded, never that it cost nothing", async () => {
    render(<SpendPage />);
    const byDay = within(await screen.findByRole("region", { name: "By day" }));
    expect(byDay.getByRole("row", { name: /2026-09-26/ })).toHaveTextContent("not recorded");
    expect(byDay.getByRole("row", { name: /2026-09-26/ })).not.toHaveTextContent("$0");
    expect(byDay.getByRole("row", { name: /2026-09-27/ })).toHaveTextContent("$8.00");
  });

  it("sums each stage over the period, most expensive first, with its share and cache", async () => {
    render(<SpendPage />);
    const rows = within(await screen.findByRole("region", { name: "By stage" })).getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("extract-shared");
    expect(rows[0]).toHaveTextContent("$10.20");
    expect(rows[0]).toHaveTextContent("68%"); // 10.2 of 15
    expect(rows[0]).toHaveTextContent("44%"); // 15.36M cached of 35.2M input
    expect(rows[1]).toHaveTextContent("gate-classify");
  });

  it("gives the runway to the floor from the recorded days' average only", async () => {
    render(<SpendPage />);
    const balance = within(await screen.findByRole("region", { name: "Balance" }));
    expect(balance.getByRole("row", { name: /Average per recorded day/ })).toHaveTextContent("$7.50");
    // (12.58 - 5) / 7.5
    expect(balance.getByRole("row", { name: /Runway to the floor/ })).toHaveTextContent("1.0 days");
    expect(runwayDays({ ...ledger, balance: null })).toBeNull();
    expect(byStage(ledger).map((s) => s.calls)).toEqual([4400, 1700]);
  });

  it("says nothing is recorded yet instead of drawing empty tables", async () => {
    fetchSpend.mockResolvedValue({ ...ledger, days: ledger.days.map((d) => ({ ...d, recorded: false, stages: [], cost: 0, calls: 0 })) });
    render(<SpendPage />);
    expect(await screen.findByText("Nothing recorded yet")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "By stage" })).not.toBeInTheDocument();
  });

  it("re-reads on a new period", async () => {
    render(<SpendPage />);
    await userEvent.click(await screen.findByRole("tab", { name: "30 days" }));
    expect(fetchSpend).toHaveBeenLastCalledWith(ADMIN.session, 30);
  });
});
