import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CancelSheet } from "@/components/CancelSheet";
import { PlanCard, planState, refundOpen } from "@/components/PlanCard";

const billing = vi.hoisted(() => ({
  fetchPlans: vi.fn(),
  fetchMySubscription: vi.fn(),
  cancelSubscription: vi.fn(),
  pauseSubscription: vi.fn(),
  refundSubscription: vi.fn(),
  resumeSubscription: vi.fn(),
  subscribe: vi.fn(),
}));
vi.mock("@/lib/billing", async (orig) => ({ ...(await orig<typeof import("@/lib/billing")>()), ...billing }));

const session = { token: "t", userId: "u1", email: "a@b.c" };
const PLANS = {
  offer: true, offer_ends: null, founding_left: 500, checkout_ready: true, key_id: "rzp_test_x",
  plans: [
    { plan: "plus_monthly", label: "Plus · monthly", amount_paise: 14900, period: "month" },
    { plan: "plus_yearly", label: "Plus · yearly", amount_paise: 149900, period: "year" },
  ],
};
const MONTHLY = { plan: "plus_monthly", status: "active", current_period_end: "2026-10-20T00:00:00Z", cancel_at: null, price_paise: 14900 };

beforeEach(() => {
  vi.clearAllMocks();
  billing.fetchPlans.mockResolvedValue(PLANS);
});

describe("CancelSheet — the truth first, one offer matched to the reason, the exit always beside it", () => {
  const sheet = (props: Partial<React.ComponentProps<typeof CancelSheet>> = {}) =>
    render(<CancelSheet open onClose={() => {}} session={session} sub={MONTHLY} onPaused={() => {}} onCancelled={() => {}} onSwitched={() => {}} {...props} />);

  it("says what cancelling does and offers nothing until a reason is given; Cancel anyway is there from the start", async () => {
    sheet();
    expect(screen.getByRole("dialog", { name: "Before you go" })).toBeInTheDocument();
    expect(screen.getByText(/You keep Plus until 20 Oct 2026\. Paid time is never taken back/)).toBeInTheDocument();
    expect(screen.queryByText("Pause instead")).toBeNull();
    expect(screen.getByRole("button", { name: "Cancel anyway" })).toBeEnabled();
    await userEvent.click(screen.getByRole("button", { name: "Not using it enough" }));
    expect(screen.getByText("Pause instead")).toBeInTheDocument();
    // Never two offers at once.
    expect(screen.queryByText(/Switch to yearly/)).toBeNull();
    expect(screen.getByRole("button", { name: "Cancel anyway" })).toBeEnabled();
  });

  it("matches the one offer to the reason: the yearly plan for price, a pause otherwise", async () => {
    sheet();
    await userEvent.click(screen.getByRole("button", { name: "Too expensive" }));
    // 12 × 149 − 1,499 = 289: arithmetic on the API's own prices.
    expect(await screen.findByText("Switch to yearly · ₹1,499")).toBeInTheDocument();
    expect(screen.getByText(/Save ₹289 a year against monthly\. Starts 20 Oct 2026, nothing charged twice/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Switch to yearly" })).toBeInTheDocument();
    expect(screen.queryByText("Pause instead")).toBeNull();
    expect(screen.getByRole("button", { name: "Cancel anyway" })).toBeEnabled();
    await userEvent.click(screen.getByRole("button", { name: "Missing something" }));
    expect(screen.queryByText(/Switch to yearly/)).toBeNull();
    expect(screen.getByText("Pause instead")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/What's missing/)).toBeInTheDocument();
  });

  it("a pause shows when Plus returns before it is taken, pauses for the months chosen, and says so", async () => {
    billing.pauseSubscription.mockResolvedValue({ paused_until: "2026-12-19T00:00:00Z", paid_until: "2026-10-20T00:00:00Z" });
    const onPaused = vi.fn();
    sheet({ onPaused });
    await userEvent.click(screen.getByRole("button", { name: "Not using it enough" }));
    expect(screen.queryByRole("button", { name: /Pause for/ })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "3 months" }));
    expect(screen.getByRole("button", { name: "3 months" })).toHaveAttribute("aria-pressed", "true");
    // The route's rule: the paid period's end + 30 days a month.
    expect(screen.getByText(/Plus until 20 Oct 2026 · resumes 18 Jan 2027/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Pause for 3 months" }));
    expect(billing.pauseSubscription).toHaveBeenCalledWith("t", 3);
    expect(await screen.findByRole("status")).toHaveTextContent(/Plus is paused.*Plus stays on until 20 Oct 2026, then pauses.*resumes on 19 Dec 2026/);
    expect(onPaused).toHaveBeenCalledWith("2026-12-19T00:00:00Z");
  });

  it("cancel anyway sends the reason and the one line, and says when Plus ends", async () => {
    billing.cancelSubscription.mockResolvedValue({ access_until: "2026-10-20T00:00:00Z" });
    const onCancelled = vi.fn();
    sheet({ onCancelled });
    await userEvent.click(screen.getByRole("button", { name: "Missing something" }));
    await userEvent.type(screen.getByPlaceholderText(/What's missing/), "  Hindi sources  ");
    await userEvent.click(screen.getByRole("button", { name: "Cancel anyway" }));
    expect(billing.cancelSubscription).toHaveBeenCalledWith("t", { reason: "missing-something", comment: "Hindi sources" });
    expect(await screen.findByRole("status")).toHaveTextContent(/Plus will end on 20 Oct 2026.*No further charges/);
    expect(onCancelled).toHaveBeenCalledWith("2026-10-20T00:00:00Z");
  });

  it("when Razorpay cannot pause, the sheet says so and the exit stays", async () => {
    billing.pauseSubscription.mockRejectedValue(new Error("unavailable"));
    sheet();
    await userEvent.click(screen.getByRole("button", { name: "Something else" }));
    await userEvent.click(screen.getByRole("button", { name: "2 months" }));
    await userEvent.click(screen.getByRole("button", { name: "Pause for 2 months" }));
    expect(await screen.findByRole("status")).toHaveTextContent(/not available on this plan yet/);
    expect(screen.queryByRole("button", { name: /Pause for/ })).toBeNull();
    expect(screen.getByRole("button", { name: "Cancel anyway" })).toBeEnabled();
  });

  it("the yearly switch starts when the month ends; a decline is said at the top and the exit stays", async () => {
    billing.subscribe.mockImplementation(async (_p: string, _t: string, _e: string, onEvent?: (k: string, d: string) => void) => {
      onEvent?.("payment_failed", "Card declined");
      await new Promise(() => {});
    });
    sheet();
    await userEvent.click(screen.getByRole("button", { name: "Too expensive" }));
    await userEvent.click(await screen.findByRole("button", { name: "Switch to yearly" }));
    expect(billing.subscribe).toHaveBeenCalledWith("plus_yearly", "t", "a@b.c", expect.any(Function), { startAfterCurrent: true });
    expect(await screen.findByRole("alert")).toHaveTextContent(/The payment did not go through.*Card declined\. Nothing was charged/);
    expect(screen.getByRole("button", { name: "Opening…" })).toBeDisabled();
  });

  it("a Razorpay outage is said in words: nothing changed, try again", async () => {
    billing.cancelSubscription.mockRejectedValue(new Error("cancel 502"));
    sheet();
    await userEvent.click(screen.getByRole("button", { name: "Cancel anyway" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Couldn't cancel: Razorpay did not answer and nothing changed. Try again in a minute.");
  });
});

describe("PlanCard — every state in one line, one action", () => {
  it("reads each state of the subscription's life", () => {
    expect(planState(null)).toBe("free");
    expect(planState({ plan: "plus_monthly", status: "active" })).toBe("active");
    expect(planState({ plan: "plus_monthly", status: "active", cancel_at: "2026-10-20T00:00:00Z" })).toBe("ending");
    expect(planState({ plan: "plus_monthly", status: "paused", paused_until: "2026-12-19T00:00:00Z" })).toBe("paused");
    expect(planState({ plan: "plus_yearly", status: "cancelled", refund_id: "rfnd_1" })).toBe("refunded");
    expect(planState({ plan: "plus_yearly", status: "cancelled" })).toBe("lapsed");
    const now = Date.parse("2026-09-21T00:00:00Z");
    expect(refundOpen({ plan: "plus_yearly", status: "active", refundable_until: "2026-09-28T00:00:00Z" }, now)).toBe(true);
    expect(refundOpen({ plan: "plus_yearly", status: "active", refundable_until: "2026-09-20T00:00:00Z" }, now)).toBe(false);
    expect(refundOpen({ plan: "plus_yearly", status: "active", refundable_until: "2026-09-28T00:00:00Z", refund_id: "rfnd_1" }, now)).toBe(false);
  });

  it("a monthly Cancel opens the sheet; a yearly one confirms inline; the refund is offered only in its window", async () => {
    billing.fetchMySubscription.mockResolvedValue(MONTHLY);
    const { unmount } = render(<PlanCard session={session} />);
    await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    expect(await screen.findByRole("dialog", { name: "Before you go" })).toBeInTheDocument();
    unmount();

    billing.fetchMySubscription.mockResolvedValue({ plan: "plus_yearly", status: "active", current_period_end: "2027-09-20T00:00:00Z", price_paise: 149900, refundable_until: "2999-01-01T00:00:00Z" });
    render(<PlanCard session={session} />);
    expect(await screen.findByText(/Full refund open until/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Refund" }));
    expect(screen.getByText(/Refund ₹1,499 in full to the method you paid with\? Plus ends now/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Keep Plus" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByText(/Stop the next charge\? You keep Plus until 20 Sept? 2027/)).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("a paused plan says when it returns and offers Resume now", async () => {
    billing.fetchMySubscription.mockResolvedValue({ ...MONTHLY, status: "paused", paused_until: "2026-12-19T00:00:00Z" });
    render(<PlanCard session={session} />);
    expect(await screen.findByText(/Plus stays on until 20 Oct 2026 · resumes 19 Dec 2026/)).toBeInTheDocument();
    billing.resumeSubscription.mockResolvedValue({ status: "active" });
    billing.fetchMySubscription.mockResolvedValue({ ...MONTHLY, current_period_end: "2026-11-20T00:00:00Z" });
    await userEvent.click(screen.getByRole("button", { name: "Resume now" }));
    expect(await screen.findByText("Plus is back on · renews 20 Nov 2026")).toBeInTheDocument();
    expect(screen.getByText("Renews 20 Nov 2026")).toBeInTheDocument();
  });
});
