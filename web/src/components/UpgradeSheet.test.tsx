import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { UpgradeSheet } from "@/components/UpgradeSheet";
import { AskPanel } from "@/components/AskPanel";
import type { AskCallbacks } from "@/lib/api";

const billing = vi.hoisted(() => ({ fetchPlans: vi.fn(), subscribe: vi.fn() }));
vi.mock("@/lib/billing", async (orig) => ({ ...(await orig<typeof import("@/lib/billing")>()), ...billing }));
const session = vi.hoisted(() => ({ current: null as null | { token: string; userId: string; email: string } }));
vi.mock("@/lib/session", async (orig) => ({ ...(await orig<typeof import("@/lib/session")>()), useSession: () => session.current }));
const askQuestion = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({ askQuestion }));

const PLANS = { offer: true, offer_ends: null, founding_left: 500, checkout_ready: true, key_id: "rzp_test_x", plans: [{ plan: "plus_monthly", label: "Plus · monthly", amount_paise: 14900, period: "month" }] };

beforeEach(() => {
  vi.clearAllMocks();
  session.current = null;
  billing.fetchPlans.mockResolvedValue(PLANS);
});

describe("UpgradeSheet", () => {
  it("says what happened in counted words and sends a stranger to sign in with the way back", async () => {
    render(<UpgradeSheet open onClose={() => {}} reason="ask-limit" used={10} limit={10} />);
    expect(screen.getByRole("dialog", { name: "You’ve asked today’s 10." })).toBeInTheDocument();
    expect(screen.getByText("10 of 10 today")).toBeInTheDocument();
    const cta = await screen.findByRole("link", { name: /Sign in to get Plus · ₹149 a month/ });
    expect(cta).toHaveAttribute("href", "/signin?next=%2Fplus%3Ffrom%3Dask-limit");
    expect(screen.getByRole("link", { name: "All plans →" })).toHaveAttribute("href", "/plus?from=ask-limit");
  });

  it("a signed-in reader pays in place and is told they are on Plus", async () => {
    session.current = { token: "t", userId: "u1", email: "a@b.c" };
    billing.subscribe.mockResolvedValue({ plan: "plus_monthly", status: "active", entitled: true });
    const onSubscribed = vi.fn();
    render(<UpgradeSheet open onClose={() => {}} reason="ask-rest" onSubscribed={onSubscribed} />);
    await userEvent.click(await screen.findByRole("button", { name: /Get Plus · ₹149 a month/ }));
    expect(billing.subscribe).toHaveBeenCalledWith("plus_monthly", "t", "a@b.c", expect.any(Function));
    expect(await screen.findByRole("status")).toHaveTextContent(/on Plus/);
    expect(onSubscribed).toHaveBeenCalled();
  });

  it("shows no dead button before the keys exist, and closes on Escape and the scrim", async () => {
    billing.fetchPlans.mockResolvedValue({ ...PLANS, checkout_ready: false });
    const onClose = vi.fn();
    render(<UpgradeSheet open onClose={onClose} />);
    expect(await screen.findByText("Plus opens soon")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Get Plus/ })).toBeNull();
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("opens from Ask's limit note for a free account at its cap", async () => {
    let cb: AskCallbacks | undefined;
    askQuestion.mockImplementation(async (_id, _q, _s, callbacks: AskCallbacks) => { cb = callbacks; });
    render(<AskPanel eventId="e1" sourceCount={3} suggestedQuestions={[]} open onOpenChange={() => {}} launcher={false} />);
    await userEvent.type(screen.getByPlaceholderText(/ask anything/i), "why?{Enter}");
    act(() => cb!.onError("question limit reached", { status: 429, used: 10, limit: 10, plus_helps: true }));
    await userEvent.click(await screen.findByRole("button", { name: "Plus is 100 a day →" }));
    expect(screen.getByRole("dialog", { name: "You’ve asked today’s 10." })).toBeInTheDocument();
  });
});
