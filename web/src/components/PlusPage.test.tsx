import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PlusPage } from "@/components/PlusPage";
import { PlanCard } from "@/components/PlanCard";
import { Payments } from "@/components/Payments";

const billing = vi.hoisted(() => ({
  fetchPlans: vi.fn(),
  subscribe: vi.fn(),
  fetchMySubscription: vi.fn(),
  cancelSubscription: vi.fn(),
  fetchPayments: vi.fn(),
}));
vi.mock("@/lib/billing", async (orig) => ({ ...(await orig<typeof import("@/lib/billing")>()), ...billing }));
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams(""), useRouter: () => router }));
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

  it("a signed-in reader subscribes to the period shown, then lands on the welcome page", async () => {
    session.current = { token: "t", userId: "u1", email: "a@b.c" };
    billing.subscribe.mockResolvedValue({ plan: "plus_yearly", status: "active", entitled: true });
    render(<PlusPage />);
    await userEvent.click((await screen.findAllByRole("button", { name: /Get Plus/ }))[0]);
    expect(billing.subscribe).toHaveBeenCalledWith("plus_yearly", "t", "a@b.c", expect.any(Function));
    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/plus/welcome"));
  });

  it("a declined card does not end the purchase: it is said, and the sheet stays open", async () => {
    session.current = { token: "t", userId: "u1", email: "a@b.c" };
    billing.subscribe.mockImplementation(async (_p: string, _t: string, _e: string, onEvent?: (k: string, d: string) => void) => {
      onEvent?.("payment_failed", "Card declined");
      await new Promise(() => {}); // the sheet is still open
      return { plan: "plus_yearly", status: "active", entitled: true };
    });
    render(<PlusPage />);
    await userEvent.click((await screen.findAllByRole("button", { name: /Get Plus/ }))[0]);
    expect(await screen.findByRole("alert")).toHaveTextContent(/The payment did not go through.*Card declined\. Nothing was charged; Razorpay’s sheet is still open/);
    expect(screen.getAllByRole("button", { name: "Opening…" })[0]).toBeDisabled();
  });

  it("a dismissed sheet says nothing; a failed one says so", async () => {
    session.current = { token: "t", userId: "u1", email: "a@b.c" };
    billing.subscribe.mockRejectedValueOnce(new Error("dismissed"));
    render(<PlusPage />);
    await userEvent.click((await screen.findAllByRole("button", { name: /Get Plus/ }))[0]);
    await waitFor(() => expect(billing.subscribe).toHaveBeenCalled());
    expect(screen.queryByRole("alert")).toBeNull();
    billing.subscribe.mockRejectedValueOnce(new Error("payment failed"));
    await userEvent.click((await screen.findAllByRole("button", { name: /Get Plus/ }))[0]);
    expect(await screen.findByRole("alert")).toHaveTextContent("payment failed");
    // "Try again" reopens checkout for the same plan.
    billing.subscribe.mockRejectedValueOnce(new Error("dismissed"));
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(billing.subscribe).toHaveBeenLastCalledWith("plus_yearly", "t", "a@b.c", expect.any(Function));
  });

  it("answers the questions people ask before paying, and names who charges them", async () => {
    render(<PlusPage />);
    await screen.findByRole("article", { name: "Plus" });
    expect(screen.getByText("Who charges me, and how?")).toBeInTheDocument();
    expect(screen.getByText(/collected by Matryx Social Labs Private Limited on behalf of Prism Media Intelligence LLP/)).toBeInTheDocument();
    expect(screen.getByRole("table")).toHaveTextContent("Questions a day");
  });
});

describe("PlanCard — every state of a subscription's life", () => {
  const s = { token: "t", userId: "u1", email: "a@b.c" };

  it("free: the way to Plus", async () => {
    billing.fetchMySubscription.mockResolvedValue({ plan: "free" });
    render(<PlanCard session={s} />);
    expect(await screen.findByRole("link", { name: "Get Plus" })).toHaveAttribute("href", "/plus?from=account");
  });

  it("active: renews on a date; cancelling a monthly is one click to the sheet and one more out, and keeps access to the period's end", async () => {
    billing.fetchMySubscription.mockResolvedValue({ plan: "plus_monthly", status: "active", current_period_end: "2026-10-20T00:00:00Z", cancel_at: null, price_paise: 14900 });
    billing.cancelSubscription.mockResolvedValue({ access_until: "2026-10-20T00:00:00Z" });
    render(<PlanCard session={s} />);
    expect(await screen.findByText("Plus · monthly")).toBeInTheDocument();
    expect(screen.getByText(/Renews 20 Oct 2026/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(billing.cancelSubscription).not.toHaveBeenCalled();
    expect(await screen.findByRole("dialog", { name: "Before you go" })).toBeInTheDocument();
    expect(screen.getByText(/You keep Plus until 20 Oct 2026/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cancel anyway" }));
    expect(billing.cancelSubscription).toHaveBeenCalledWith("t", { reason: undefined, comment: undefined });
    expect(await screen.findByText(/Ends 20 Oct 2026 · no further charges/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).toBeNull();
  });

  it("past due: says the charge failed and until when access lasts, and points at the email", async () => {
    billing.fetchMySubscription.mockResolvedValue({ plan: "plus_yearly", status: "past_due", current_period_end: "2026-10-01T00:00:00Z", cancel_at: null, price_paise: 119900 });
    render(<PlanCard session={s} />);
    expect(await screen.findByText(/The last charge did not go through/)).toBeInTheDocument();
    expect(screen.getByText(/The last charge did not go through · Plus stays on until 1 Oct 2026/)).toBeInTheDocument();
    // Said above the card too, with the amount and what to do.
    expect(screen.getByRole("alert")).toHaveTextContent(/A charge did not go through.*could not take ₹1,199.*until 1 Oct 2026.*update the payment method/);
    expect(screen.getByText("Check your email")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).toBeNull();
  });

  it("lapsed: says when it ended and offers Plus again", async () => {
    billing.fetchMySubscription.mockResolvedValue({ plan: "plus_monthly", status: "cancelled", current_period_end: "2026-09-01T00:00:00Z", cancel_at: "2026-09-01T00:00:00Z", price_paise: 14900 });
    render(<PlanCard session={s} />);
    expect(await screen.findByText(/Your Plus ended on 1 Sept 2026/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Get Plus" })).toBeInTheDocument();
  });
});

describe("Payments — every charge from Razorpay's history, in words", () => {
  const s = { token: "t", userId: "u1", email: "a@b.c" };

  it("prints each charge with its state and invoice, a refund on a dashed tag, and says where receipts come from", async () => {
    billing.fetchPayments.mockResolvedValue([
      { paid_at: "2026-09-24T04:00:00Z", plan: "plus_yearly", amount_paise: 119900, status: "refunded", invoice_url: "https://rzp.io/i/a", invoice_id: "inv_a", payment_id: "pay_a" },
      { paid_at: "2026-08-24T04:00:00Z", plan: "plus_monthly", amount_paise: 14900, status: "paid", invoice_url: "https://rzp.io/i/b", invoice_id: "inv_b", payment_id: "pay_b" },
    ]);
    render(<Payments session={s} />);
    expect(screen.getByText("RECEIPTS AND INVOICES COME FROM RAZORPAY")).toBeInTheDocument();
    const refunded = await screen.findByText("refunded");
    expect(refunded).toHaveStyle({ borderStyle: "dashed" });
    expect(screen.getByText("paid")).toHaveStyle({ borderStyle: "solid" });
    expect(screen.getAllByRole("link", { name: /Invoice/ })[0]).toHaveAttribute("href", "https://rzp.io/i/a");
  });

  it("says 'No charges yet' before the first, and a Razorpay failure in words with a retry", async () => {
    billing.fetchPayments.mockResolvedValueOnce([]);
    const { unmount } = render(<Payments session={s} />);
    expect(await screen.findByText("No charges yet.")).toBeInTheDocument();
    unmount();
    billing.fetchPayments.mockRejectedValueOnce(new Error("history 502"));
    render(<Payments session={s} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/Payments could not load.*Razorpay did not answer\. Your plan is not affected/);
    billing.fetchPayments.mockResolvedValueOnce([]);
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("No charges yet.")).toBeInTheDocument();
  });
});
