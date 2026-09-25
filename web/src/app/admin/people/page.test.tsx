import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import PeoplePage from "@/app/admin/people/page";

const fetchPeople = vi.hoisted(() => vi.fn());
const adminCall = vi.hoisted(() => vi.fn());
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({ ...(await orig<typeof import("@/components/admin/AdminShell")>()), useAdmin: () => ADMIN }));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchPeople, adminCall }));

const person = (over: Record<string, unknown>) => ({
  email: "a@example.test", name: null, profession: null, languages: [], state: null, created_at: "2026-09-20T10:00:00Z",
  plan: null, plan_status: null, provider: null, active_days: 0, active_on: [], last_active: null, labeller: null, ...over,
});

beforeEach(() => {
  fetchPeople.mockReset().mockResolvedValue({
    total: 2, active_window_days: 28, window_start: "2026-08-27",
    people: [
      person({ email: "paid@example.test", name: "Asha", profession: "journalist", languages: ["kn"], plan: "plus_monthly", plan_status: "active", provider: "razorpay", active_days: 2, active_on: ["2026-09-20", "2026-09-23"], last_active: "2026-09-23", labeller: "active" }),
      person({ email: "gift@example.test", plan: "plus_yearly", plan_status: "active", provider: "manual" }),
    ],
  });
});

describe("people", () => {
  it("lists each account with its plan, activity and labelling", async () => {
    render(<PeoplePage />);
    const row = within((await screen.findByText("paid@example.test")).closest("tr")!);
    expect(row.getByText("Asha · journalist · Kannada")).toBeInTheDocument();
    expect(row.getByText("plus monthly · active")).toBeInTheDocument();
    expect(row.getByText(/LAST 23 SEP/)).toBeInTheDocument();
    expect(screen.getByText("NEWEST FIRST · 2 ACCOUNTS")).toBeInTheDocument();
  });

  it("never prints a total above rows that are not all there", async () => {
    fetchPeople.mockResolvedValue({ total: 812, active_window_days: 28, window_start: "2026-08-27", people: [person({ email: "one@example.test" })] });
    render(<PeoplePage />);
    expect(await screen.findByText("NEWEST FIRST · SHOWING THE NEWEST 1 OF 812")).toBeInTheDocument();
    expect(screen.queryByText(/812 ACCOUNTS/)).not.toBeInTheDocument();
    // The rest load on request, from where the loaded rows end.
    fetchPeople.mockClear();
    adminCall.mockResolvedValue({ total: 812, active_window_days: 28, window_start: "2026-08-27", people: [person({ email: "two@example.test" })] });
    await userEvent.click(screen.getByRole("button", { name: "Load the next 500" }));
    expect(adminCall).toHaveBeenCalledWith(expect.anything(), "/api/v1/admin/people?limit=500&offset=1");
    expect(await screen.findByText("two@example.test")).toBeInTheDocument();
    expect(screen.getByText("NEWEST FIRST · SHOWING THE NEWEST 2 OF 812")).toBeInTheDocument();
  });

  it("marks a given plan as given, not as revenue", async () => {
    render(<PeoplePage />);
    const row = within((await screen.findByText("gift@example.test")).closest("tr")!);
    expect(row.getByText("plus yearly · active · given")).toBeInTheDocument();
    expect(row.getByText("Nothing told us yet")).toBeInTheDocument();
  });

  it("draws each day of the window, marking only the days they were active", async () => {
    render(<PeoplePage />);
    const row = within((await screen.findByText("paid@example.test")).closest("tr")!);
    const strip = row.getByRole("img", { name: "Active on 2 of the last 28 days, last on 23 Sept" });
    const marks = Array.from(strip.children) as HTMLElement[];
    expect(marks).toHaveLength(28);
    expect(marks.filter((m) => m.style.background === "var(--ink)")).toHaveLength(2);
    // 27 Aug + 24 = 20 Sep and + 27 = 23 Sep: the marks sit on those days.
    expect(marks[24].style.background).toBe("var(--ink)");
    expect(marks[27].style.background).toBe("var(--ink)");
  });

  it("filters by plan and finds an account by what they told us", async () => {
    render(<PeoplePage />);
    await screen.findByText("paid@example.test");
    await userEvent.click(screen.getByRole("radio", { name: /Given/ }));
    expect(screen.queryByText("paid@example.test")).not.toBeInTheDocument();
    expect(screen.getByText("NEWEST FIRST · 2 ACCOUNTS · 1 MATCH")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: /All/ }));
    await userEvent.type(screen.getByRole("searchbox"), "journalist");
    expect(screen.getByText("paid@example.test")).toBeInTheDocument();
    expect(screen.queryByText("gift@example.test")).not.toBeInTheDocument();
  });

  it("calls a checkout left open or a plan that ended free, and says which plan it was", async () => {
    fetchPeople.mockResolvedValue({
      total: 1, active_window_days: 28, window_start: "2026-08-27",
      people: [person({ email: "left@example.test", plan: "plus_monthly", plan_status: "created", provider: "razorpay" })],
    });
    render(<PeoplePage />);
    const row = within((await screen.findByText("left@example.test")).closest("tr")!);
    expect(row.getByText("Free")).toBeInTheDocument();
    expect(row.getByText("plus monthly · created")).toBeInTheDocument();
  });
});
