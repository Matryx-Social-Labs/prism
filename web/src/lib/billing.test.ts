import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { gstBreakup, gstIncluded, rupees, subscribe } from "@/lib/billing";

// E-Com Rules R7(1)(e): one total, with the tax inside it broken out. Prices
// are GST-inclusive (founder, 2026-09-29), so the base is total ÷ 1.18.
describe("gstBreakup — the GST inside every price on sale", () => {
  it.each([
    [14900, "₹149", "₹126.27", "₹22.73"],
    [99900, "₹999", "₹846.61", "₹152.39"],
    [119900, "₹1,199", "₹1,016.10", "₹182.90"],
    [149900, "₹1,499", "₹1,270.34", "₹228.66"],
    [19900, "₹199", "₹168.64", "₹30.36"],
  ])("%i paise is %s: %s + %s GST", (paise, total, base, gst) => {
    expect(gstBreakup(paise)).toEqual({ total, base, gst });
  });

  it("says it compactly, and whole rupees still print without paise", () => {
    expect(gstIncluded(14900)).toBe("including ₹22.73 GST (18%)");
    expect(rupees(119900)).toBe("₹1,199");
    expect(rupees(12627)).toBe("₹126.27");
    expect(rupees(12620)).toBe("₹126.20");
  });
});

// A checkout that did not pay was counted nowhere: closed, declined and
// unverifiable all looked like a reader who never tried (audit 2026-09-29, §2.5).
const track = vi.hoisted(() => vi.fn());
vi.mock("@/lib/analytics", () => ({ track }));

type Opts = { handler: (r: unknown) => void; modal: { ondismiss: () => void } };
let sheet: { opts: Opts; failed?: (r: unknown) => void };

const ORDER = { subscription_id: "sub_1", key_id: "rzp_test_x", label: "Plus · monthly", amount_paise: 14900 };
const PAID = { razorpay_payment_id: "pay_1", razorpay_subscription_id: "sub_1", razorpay_signature: "sig" };

function stubCheckout(verifyOk: boolean) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) =>
    url.endsWith("/billing/checkout")
      ? new Response(JSON.stringify(ORDER), { status: 200 })
      : new Response(JSON.stringify({ plan: "plus_monthly", status: "active", entitled: true }), { status: verifyOk ? 200 : 502 })));
  window.Razorpay = class {
    constructor(opts: Record<string, unknown>) {
      sheet = { opts: opts as unknown as Opts };
    }
    on(_ev: string, cb: (r: unknown) => void) {
      sheet.failed = cb;
    }
    open() {}
  };
}

const stages = () => track.mock.calls.map(([, p]) => (p as { stage: string }).stage);
const opened = async () => vi.waitFor(() => expect(sheet?.opts).toBeDefined());

beforeEach(() => {
  track.mockReset();
  sheet = undefined as unknown as typeof sheet;
});
afterEach(() => {
  vi.unstubAllGlobals();
  delete window.Razorpay;
});

describe("subscribe — how a checkout that did not pay ended", () => {
  it("counts a sheet closed without paying", async () => {
    stubCheckout(true);
    const done = subscribe("plus_monthly", "t", "a@b.c");
    await opened();
    sheet.opts.modal.ondismiss();
    await expect(done).rejects.toThrow("dismissed");
    expect(stages()).toEqual(["checkout", "dismissed"]);
  });

  it("counts a declined payment, and the purchase goes on to pay", async () => {
    stubCheckout(true);
    const done = subscribe("plus_monthly", "t", "a@b.c");
    await opened();
    sheet.failed!({ error: { description: "Card declined" } });
    sheet.opts.handler(PAID);
    await expect(done).resolves.toMatchObject({ entitled: true });
    expect(stages()).toEqual(["checkout", "declined", "paid"]);
  });

  it("counts a payment the server could not confirm", async () => {
    stubCheckout(false);
    const done = subscribe("plus_monthly", "t", "a@b.c");
    await opened();
    sheet.opts.handler(PAID);
    await expect(done).rejects.toThrow(/could not confirm/);
    expect(stages()).toEqual(["checkout", "unverified"]);
    expect(track).toHaveBeenLastCalledWith("Subscribe", { plan: "plus_monthly", stage: "unverified" });
  });
});
