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

describe("CancelSheet — one screen, the truth first, one offer, the exit beside it", () => {
  it("says what cancelling does, offers a pause by default, and keeps Cancel anyway on the same row", async () => {
    render(<CancelSheet open onClose={() => {}} session={session} sub={MONTHLY} onPaused={() => {}} onCancelled={() => {}} onSwitched={() => {}} />);
    expect(screen.getByRole("dialog", { name: "Before you go" })).toBeInTheDocument();
    expect(screen.getByText(/You keep Plus until 20 Oct 2026/)).toBeInTheDocument();
    expect(screen.getByText("Take a break instead?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pause for 2 months" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel anyway" })).toBeEnabled();
    // Never two offers at once (one retention offer, shown with the exit).
    expect(screen.queryByText(/Yearly is/)).toBeNull();
  });

  it("matches the one offer to the reason: the yearly saving for price, nothing for a missing feature", async () => {
    render(<CancelSheet open onClose={() => {}} session={session} sub={MONTHLY} onPaused={() => {}} onCancelled={() => {}} onSwitched={() => {}} />);
    await screen.findByText("Take a break instead?");
    await userEvent.click(screen.getByRole("button", { name: "Too expensive" }));
    expect(await screen.findByText("Yearly is ₹125 a month")).toBeInTheDocument();
    expect(screen.getByText(/₹1,499 a year — ₹289 less than twelve months/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Switch to yearly · ₹1,499/ })).toBeInTheDocument();
    expect(screen.queryByText("Take a break instead?")).toBeNull();
    expect(screen.getByRole("button", { name: "Cancel anyway" })).toBeEnabled();
    await userEvent.click(screen.getByRole("button", { name: "Missing something" }));
    expect(screen.queryByText(/Yearly is/)).toBeNull();
    expect(screen.queryByText("Take a break instead?")).toBeNull();
    expect(screen.getByPlaceholderText(/What was missing/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel anyway" })).toBeEnabled();
  });

  it("a pause pauses for the chosen months and reports when Plus returns; cancel anyway sends the reason", async () => {
    billing.pauseSubscription.mockResolvedValue({ paused_until: "2026-12-19T00:00:00Z", paid_until: "2026-10-20T00:00:00Z" });
    const onPaused = vi.fn();
    render(<CancelSheet open onClose={() => {}} session={session} sub={MONTHLY} onPaused={onPaused} onCancelled={() => {}} onSwitched={() => {}} />);
    await userEvent.click(await screen.findByRole("radio", { name: "3 months" }));
    await userEvent.click(screen.getByRole("button", { name: "Pause for 3 months" }));
    expect(billing.pauseSubscription).toHaveBeenCalledWith("t", 3);
    expect(await screen.findByRole("status")).toHaveTextContent(/Plus stays on until 20 Oct 2026.*comes back on 19 Dec 2026/);
    expect(onPaused).toHaveBeenCalledWith("2026-12-19T00:00:00Z");

    billing.cancelSubscription.mockResolvedValue({ access_until: "2026-10-20T00:00:00Z" });
    const onCancelled = vi.fn();
    render(<CancelSheet open onClose={() => {}} session={session} sub={MONTHLY} onPaused={() => {}} onCancelled={onCancelled} onSwitched={() => {}} />);
    await userEvent.click((await screen.findAllByRole("button", { name: "Not using it enough" }))[0]);
    await userEvent.click(screen.getAllByRole("button", { name: "Cancel anyway" })[0]);
    expect(billing.cancelSubscription).toHaveBeenCalledWith("t", { reason: "not-using", comment: undefined });
    expect(onCancelled).toHaveBeenCalledWith("2026-10-20T00:00:00Z");
  });

  it("when Razorpay cannot pause, the sheet says so and the exit stays", async () => {
    billing.pauseSubscription.mockRejectedValue(new Error("unavailable"));
    render(<CancelSheet open onClose={() => {}} session={session} sub={MONTHLY} onPaused={() => {}} onCancelled={() => {}} onSwitched={() => {}} />);
    await userEvent.click(await screen.findByRole("button", { name: "Pause for 2 months" }));
    expect(await screen.findByRole("status")).toHaveTextContent(/not available on this plan yet/);
    expect(screen.queryByRole("button", { name: /Pause for/ })).toBeNull();
    expect(screen.getByRole("button", { name: "Cancel anyway" })).toBeEnabled();
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
    expect(await screen.findByText(/Paused · Plus stays on until 20 Oct 2026 · resumes 19 Dec 2026 on its own/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resume now" })).toBeInTheDocument();
  });
});
