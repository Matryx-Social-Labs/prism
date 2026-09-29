import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import GrievancesPage from "@/app/admin/grievances/page";

const fetchGrievances = vi.hoisted(() => vi.fn());
const decideGrievance = vi.hoisted(() => vi.fn());
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({ ...(await orig<typeof import("@/components/admin/AdminShell")>()), useAdmin: () => ADMIN }));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchGrievances, decideGrievance }));

const g = (ref: string, over = {}) => ({
  ref, created_at: "2026-09-29T08:30:00Z", decide_by: "2099-10-14T08:30:00Z", name: "Asha", email: "asha@example.test",
  category: "A fact is wrong", subject_url: "/story/abc", body: "The date is wrong.", status: "open",
  acknowledged_at: "2026-09-29T08:30:01Z", resolved_at: null, outcome: null, ...over,
});

beforeEach(() => {
  fetchGrievances.mockReset().mockResolvedValue({
    decide_within_days: 15,
    grievances: [
      g("PG-1", { acknowledged_at: null, decide_by: "2026-09-01T00:00:00Z" }),
      g("PG-2", { status: "resolved", resolved_at: "2026-09-30T08:30:00Z", outcome: "Corrected the date." }),
    ],
  });
  decideGrievance.mockReset().mockResolvedValue({ ref: "PG-1", status: "resolved", emailed: true });
});

describe("the grievance queue", () => {
  it("shows open complaints first, with the clock, a failed acknowledgement and an overdue one said in words", async () => {
    render(<GrievancesPage />);
    const row = within(await screen.findByRole("listitem", { name: "PG-1" }));
    expect(row.getByText("NOT ACKNOWLEDGED BY EMAIL")).toBeInTheDocument();
    expect(row.getByText("OVERDUE")).toBeInTheDocument();
    expect(row.getByText("The date is wrong.")).toBeInTheDocument();
    expect(row.getByRole("link", { name: "/story/abc" })).toHaveAttribute("href", "/story/abc");
    expect(screen.queryByRole("listitem", { name: "PG-2" })).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Resolved/ })).toHaveTextContent("1");
    await userEvent.click(screen.getByRole("radio", { name: /Resolved/ }));
    expect(within(screen.getByRole("listitem", { name: "PG-2" })).getByText("Corrected the date.")).toBeInTheDocument();
  });

  it("decides only with an outcome in words, asked in place, and says whether the complainant was told", async () => {
    render(<GrievancesPage />);
    const row = within(await screen.findByRole("listitem", { name: "PG-1" }));
    expect(row.getByRole("button", { name: "Resolve" })).toBeDisabled();
    await userEvent.type(row.getByLabelText(/Outcome, as the complainant will read it/), "  The date was corrected.  ");
    await userEvent.click(row.getByRole("button", { name: "Resolve" }));
    expect(decideGrievance).not.toHaveBeenCalled();
    await userEvent.click(row.getByRole("button", { name: "Yes, resolve" }));
    expect(decideGrievance).toHaveBeenCalledWith(ADMIN.session, "PG-1", "resolved", "The date was corrected.");
    expect(await screen.findByText("PG-1 is resolved, and the outcome was emailed to asha@example.test.")).toBeInTheDocument();
    expect(fetchGrievances).toHaveBeenCalledTimes(2);
  });

  it("says when the outcome could not be emailed", async () => {
    decideGrievance.mockResolvedValue({ ref: "PG-1", status: "rejected", emailed: false });
    render(<GrievancesPage />);
    const row = within(await screen.findByRole("listitem", { name: "PG-1" }));
    await userEvent.type(row.getByLabelText(/Outcome/), "Not upheld: the article says so.");
    await userEvent.click(row.getByRole("button", { name: "Reject" }));
    await userEvent.click(row.getByRole("button", { name: "Yes, reject" }));
    expect(await screen.findByText(/could not be emailed\. Write to asha@example\.test yourself/)).toBeInTheDocument();
  });
});
