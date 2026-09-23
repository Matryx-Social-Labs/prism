import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";

import PeoplePage from "@/app/admin/people/page";

const fetchPeople = vi.hoisted(() => vi.fn());
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({ ...(await orig<typeof import("@/components/admin/AdminShell")>()), useAdmin: () => ADMIN }));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchPeople }));

const person = (over: Record<string, unknown>) => ({
  email: "a@example.test", name: null, profession: null, languages: [], state: null, created_at: "2026-09-20T10:00:00Z",
  plan: null, plan_status: null, provider: null, active_days: 0, last_active: null, labeller: null, ...over,
});

beforeEach(() => {
  fetchPeople.mockReset().mockResolvedValue({
    total: 2, active_window_days: 28,
    people: [
      person({ email: "paid@example.test", name: "Asha", profession: "journalist", languages: ["kn"], plan: "plus_monthly", plan_status: "active", provider: "razorpay", active_days: 5, last_active: "2026-09-23", labeller: "active" }),
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
    expect(screen.getByRole("heading", { name: "Accounts · 2" })).toBeInTheDocument();
  });

  it("never prints a total above rows that are not all there", async () => {
    fetchPeople.mockResolvedValue({ total: 812, active_window_days: 28, people: [person({ email: "one@example.test" })] });
    render(<PeoplePage />);
    expect(await screen.findByRole("heading", { name: "Accounts · newest 1 of 812" })).toBeInTheDocument();
  });

  it("marks a given plan as given, not as revenue", async () => {
    render(<PeoplePage />);
    const row = within((await screen.findByText("gift@example.test")).closest("tr")!);
    expect(row.getByText("plus yearly · active · given")).toBeInTheDocument();
    expect(row.getByText("Nothing told us yet")).toBeInTheDocument();
  });
});
