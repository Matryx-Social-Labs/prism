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
    expect(screen.getByRole("dialog", { name: "Keep asking with an account" })).toBeInTheDocument();
    expect(screen.getByText("10 of 10 today")).toBeInTheDocument();
    const cta = await screen.findByRole("link", { name: "Sign in to get Plus" });
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
    session.current = { token: "t", userId: "u1", email: "a@b.c" };
    let cb: AskCallbacks | undefined;
    askQuestion.mockImplementation(async (_id, _q, _s, callbacks: AskCallbacks) => { cb = callbacks; });
    render(<AskPanel eventId="e1" sourceCount={3} suggestedQuestions={[]} open onOpenChange={() => {}} launcher={false} />);
    await userEvent.type(screen.getByPlaceholderText(/ask anything/i), "why?{Enter}");
    act(() => cb!.onError("question limit reached", { status: 429, used: 10, limit: 10, plus_helps: true }));
    await userEvent.click(await screen.findByRole("button", { name: "Plus is 100 a day →" }));
    expect(screen.getByRole("dialog", { name: "Ask more of this story" })).toBeInTheDocument();
    expect(screen.getByText("10 of 10 today")).toBeInTheDocument();
    // /plus, and sign-in through it, bring the reader back to this story (audit 2026-09-29, P1-3).
    expect(screen.getByRole("link", { name: "All plans →" })).toHaveAttribute("href", "/plus?from=ask-limit&next=%2Fstory%2Fe1");
  });

  // COMPLIANCE-INDIA N7: what renews, how often and at what price is said
  // BEFORE the button that opens the mandate, in the API's figures.
  it("says what renews, at the API's price, above the button that opens the mandate", async () => {
    session.current = { token: "t", userId: "u1", email: "a@b.c" };
    billing.fetchPlans.mockResolvedValue({ ...PLANS, plans: [{ ...PLANS.plans[0], amount_paise: 19900 }] });
    render(<UpgradeSheet open onClose={() => {}} reason="ask-limit" />);
    const button = await screen.findByRole("button", { name: "Get Plus · ₹199 a month" });
    const terms = screen.getByText(/₹199 today, then ₹199 every month until you cancel/);
    // E-Com Rules R7(1)(e): the GST inside the price, beside it.
    expect(terms).toHaveTextContent("until you cancel, each including ₹30.36 GST (18%).");
    expect(terms).toHaveTextContent("Cancel in one click from your account; paid time is kept.");
    expect(terms.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  // Audit 2026-09-29 P1-2/P1-3: the lens wall sells the lens first, and every
  // door carries the story the reader was on.
  it("at the lens wall leads with the lens, keeps the way back to the story, and says the lens is open", async () => {
    const stranger = render(<UpgradeSheet open onClose={() => {}} reason="lens-limit" used={10} limit={10} lensName="Markets" back="/story/e1" />);
    expect(screen.getByRole("link", { name: "All plans →" })).toHaveAttribute("href", "/plus?from=lens-limit&next=%2Fstory%2Fe1");
    expect(await screen.findByRole("link", { name: "Sign in to get Plus" })).toHaveAttribute(
      "href", `/signin?next=${encodeURIComponent("/plus?from=lens-limit&next=%2Fstory%2Fe1")}`);
    stranger.unmount();

    session.current = { token: "t", userId: "u1", email: "a@b.c" };
    billing.subscribe.mockResolvedValue({ plan: "plus_monthly", status: "active", entitled: true });
    const onSubscribed = vi.fn();
    render(<UpgradeSheet open onClose={() => {}} reason="lens-limit" used={10} limit={10} lensName="Markets" back="/story/e1" onSubscribed={onSubscribed} />);
    const dialog = screen.getByRole("dialog", { name: "Every lens on this story" });
    expect(dialog.querySelector("li")).toHaveTextContent("Every lens on every story that earns one, as often as you like");
    await userEvent.click(await screen.findByRole("button", { name: /Get Plus · ₹149 a month/ }));
    expect(await screen.findByRole("status")).toHaveTextContent("The Markets read is open.");
    expect(onSubscribed).toHaveBeenCalled();
  });

  // Founder, 2026-09-29: while founding seats are sold, the sheet points at them, on /plus, with the way back.
  it("while founding seats are sold and checkout is open, offers founding as the second way, to /plus on the year", async () => {
    const founding = { plan: "founding", label: "Founding member · yearly", amount_paise: 99900, period: "year" };
    billing.fetchPlans.mockResolvedValue({ ...PLANS, plans: [...PLANS.plans, founding] });
    const onClose = vi.fn();
    const { unmount } = render(<UpgradeSheet open onClose={onClose} reason="lens-limit" back="/story/e1" />);
    const link = await screen.findByRole("link", { name: "Or become a founding member · ₹999 a year" });
    expect(link).toHaveAttribute("href", "/plus?from=lens-limit&period=year&next=%2Fstory%2Fe1");
    expect(screen.getByRole("link", { name: "Sign in to get Plus" }).compareDocumentPosition(link) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    unmount();

    billing.fetchPlans.mockResolvedValue({ ...PLANS, checkout_ready: false, plans: [...PLANS.plans, founding] });
    render(<UpgradeSheet open onClose={onClose} reason="lens-limit" />);
    expect(await screen.findByText("Plus opens soon")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /founding member/ })).toBeNull();
  });

  it("a declined payment is said inside the sheet, and the purchase waits for the next try", async () => {
    session.current = { token: "t", userId: "u1", email: "a@b.c" };
    billing.subscribe.mockImplementation(async (_p: string, _t: string, _e: string, onEvent?: (k: string, d: string) => void) => {
      onEvent?.("payment_failed", "Card declined");
      await new Promise(() => {});
    });
    render(<UpgradeSheet open onClose={() => {}} reason="ask-limit" used={10} limit={10} />);
    await userEvent.click(await screen.findByRole("button", { name: /Get Plus · ₹149 a month/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/The payment did not go through.*Card declined\. Nothing was charged/);
    expect(screen.getByRole("button", { name: "Opening…" })).toBeDisabled();
  });
});
