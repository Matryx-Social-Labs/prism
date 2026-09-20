import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PlusPage } from "@/components/PlusPage";
import { PlanRow } from "@/components/PlanRow";

const billing = vi.hoisted(() => ({
  fetchPlans: vi.fn(),
  subscribe: vi.fn(),
  fetchMySubscription: vi.fn(),
  cancelSubscription: vi.fn(),
}));
vi.mock("@/lib/billing", async (orig) => ({ ...(await orig<typeof import("@/lib/billing")>()), ...billing }));
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams(""), useRouter: () => ({ push: vi.fn() }) }));
const session = vi.hoisted(() => ({ current: null as null | { token: string; userId: string; email: string } }));
vi.mock("@/lib/session", async (orig) => ({
  ...(await orig<typeof import("@/lib/session")>()),
  useSession: () => session.current,
  fetchMe: async () => ({ user_id: "u1", email: "a@b.c", plan: "free" }),
}));

const PLANS = {
  offer: true,
  offer_ends: null,
  founding_left: 500,
  checkout_ready: true,
  key_id: "rzp_test_x",
  plans: [
    { plan: "plus_monthly", label: "Plus · monthly", amount_paise: 14900, period: "month" },
    { plan: "plus_yearly", label: "Plus · yearly", amount_paise: 119900, period: "year" },
    { plan: "founding", label: "Founding member", amount_paise: 99900, period: "year" },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  session.current = null;
  billing.fetchPlans.mockResolvedValue(PLANS);
});

describe("PlusPage", () => {
  it("prints the API's prices, yearly by default with the saving computed from them, and sends a stranger to sign in first", async () => {
    render(<PlusPage />);
    const plus = await screen.findByRole("article", { name: "Plus" });
    expect(plus).toHaveTextContent("₹1,199");
    expect(plus).toHaveTextContent("≈ ₹100 a month");
    // 12 × 149 − 1,199 = 589: arithmetic on the API's figures, not a typed number.
    expect(screen.getByRole("tab", { name: /Yearly/ })).toHaveTextContent("save ₹589");
    expect(screen.getByRole("article", { name: "Founding member" })).toHaveTextContent("500 of 500 seats");
    expect(screen.getAllByRole("link", { name: "Sign in to continue" })[0]).toHaveAttribute("href", "/signin?next=/plus");
    expect(screen.queryByRole("button", { name: /Get Plus/ })).toBeNull();
    await userEvent.click(screen.getByRole("tab", { name: "Monthly" }));
    expect(screen.getByRole("article", { name: "Plus" })).toHaveTextContent("₹149");
  });

  it("shows no button that cannot work: before the keys exist the cards say 'Opens soon'", async () => {
    billing.fetchPlans.mockResolvedValue({ ...PLANS, checkout_ready: false, key_id: null });
    session.current = { token: "t", userId: "u1", email: "a@b.c" };
    render(<PlusPage />);
    expect((await screen.findAllByText("Opens soon")).length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByRole("button", { name: /Get Plus/ })).toBeNull();
  });

  it("a signed-in reader subscribes to the period shown, then is on Plus", async () => {
    session.current = { token: "t", userId: "u1", email: "a@b.c" };
    billing.subscribe.mockResolvedValue("plus_yearly");
    render(<PlusPage />);
    await userEvent.click((await screen.findAllByRole("button", { name: /Get Plus/ }))[0]);
    expect(billing.subscribe).toHaveBeenCalledWith("plus_yearly", "t", "a@b.c");
    expect(await screen.findByText(/You’re on Plus/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Get Plus/ })).toBeNull();
  });

  it("a dismissed sheet says nothing; a failed one says so", async () => {
    session.current = { token: "t", userId: "u1", email: "a@b.c" };
    billing.subscribe.mockRejectedValueOnce(new Error("dismissed"));
    render(<PlusPage />);
    await userEvent.click((await screen.findAllByRole("button", { name: /Get Plus/ }))[0]);
    await waitFor(() => expect(billing.subscribe).toHaveBeenCalled());
    expect(screen.queryByRole("status")).toBeNull();
    billing.subscribe.mockRejectedValueOnce(new Error("payment failed"));
    await userEvent.click((await screen.findAllByRole("button", { name: /Get Plus/ }))[0]);
    expect(await screen.findByRole("status")).toHaveTextContent("payment failed");
  });

  it("answers the questions people ask before paying, and names who charges them", async () => {
    render(<PlusPage />);
    await screen.findByRole("article", { name: "Plus" });
    expect(screen.getByText("Who charges me, and how?")).toBeInTheDocument();
    expect(screen.getByText(/collected by Matryx Social Labs Private Limited on behalf of Prism Media Intelligence LLP/)).toBeInTheDocument();
    expect(screen.getByRole("table")).toHaveTextContent("Questions a day");
  });
});

describe("PlanRow", () => {
  const s = { token: "t", userId: "u1", email: "a@b.c" };

  it("a free account sees the way to Plus", async () => {
    billing.fetchMySubscription.mockResolvedValue({ plan: "free" });
    render(<PlanRow session={s} />);
    expect(await screen.findByRole("link", { name: "Plus →" })).toHaveAttribute("href", "/plus");
  });

  it("cancelling is one click plus a confirmation, and keeps access to the period's end", async () => {
    billing.fetchMySubscription.mockResolvedValue({ plan: "plus_monthly", status: "active", current_period_end: "2026-10-20T00:00:00Z", cancel_at: null, price_paise: 14900 });
    billing.cancelSubscription.mockResolvedValue({ access_until: "2026-10-20T00:00:00Z" });
    render(<PlanRow session={s} />);
    expect(await screen.findByText("Plus · monthly")).toBeInTheDocument();
    expect(screen.getByText(/Renews 20 Oct 2026/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(billing.cancelSubscription).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Yes, cancel" }));
    expect(billing.cancelSubscription).toHaveBeenCalledWith("t");
    expect(await screen.findByText(/Ends 20 Oct 2026 · no further charges/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).toBeNull();
  });
});
