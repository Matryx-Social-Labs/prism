// Plans, checkout and the account's subscription — the client side of
// api/routes/billing.py. Checkout itself is Razorpay's hosted sheet
// (checkout.js), opened with a subscription id the server made at today's
// price; its success callback is sent back to /billing/verify, which is the
// only thing that turns Plus on.
import { API_URL, authHeaders } from "@/lib/api";
import { track } from "@/lib/analytics";

export interface PlanOut {
  plan: "plus_monthly" | "plus_yearly" | "founding" | string;
  label: string;
  amount_paise: number;
  period: "month" | "year";
}
export interface PlansOut {
  offer: boolean;
  offer_ends: string | null;
  founding_left: number;
  plans: PlanOut[];
  checkout_ready: boolean;
  key_id: string | null;
}
export interface MySubscription {
  plan: string;
  status?: string;
  current_period_end?: string | null;
  cancel_at?: string | null;
  price_paise?: number | null;
}

export const rupees = (paise: number) => `₹${(paise / 100).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

export async function fetchPlans(): Promise<PlansOut> {
  const r = await fetch(`${API_URL}/api/v1/billing/plans`, { cache: "no-store" });
  if (!r.ok) throw new Error(`plans ${r.status}`);
  return r.json();
}

export async function fetchMySubscription(token: string): Promise<MySubscription> {
  const r = await fetch(`${API_URL}/api/v1/billing/me`, { headers: authHeaders(token), cache: "no-store" });
  if (!r.ok) throw new Error(`billing/me ${r.status}`);
  return r.json();
}

export async function cancelSubscription(token: string): Promise<{ access_until: string | null }> {
  const r = await fetch(`${API_URL}/api/v1/billing/cancel`, { method: "POST", headers: authHeaders(token) });
  if (!r.ok) throw new Error(`cancel ${r.status}`);
  return r.json();
}

declare global {
  interface Window {
    Razorpay?: new (opts: Record<string, unknown>) => { open: () => void; on: (ev: string, cb: (r: unknown) => void) => void };
  }
}

function loadCheckoutJs(): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("checkout.js failed to load"));
    document.head.appendChild(s);
  });
}

export interface Subscribed {
  plan: string;
  status: string;
  entitled: boolean;
}

/**
 * Subscribe: make the subscription, open Razorpay's sheet, verify the callback.
 * Resolves when Plus is on; rejects only when the sheet is closed without
 * paying ("dismissed") or the callback cannot be verified. A declined card is
 * NOT the end — Razorpay keeps the sheet open for another method — so a
 * `payment.failed` event is reported through `onEvent` and the flow waits.
 * (The first real test purchase was lost exactly there: a declined card
 * ended our promise, the UPI payment that followed succeeded unheard.)
 */
export async function subscribe(plan: string, token: string, email: string | undefined, onEvent?: (kind: "payment_failed", detail: string) => void): Promise<Subscribed> {
  track("Subscribe", { plan, stage: "checkout" });
  const r = await fetch(`${API_URL}/api/v1/billing/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify({ plan }),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(typeof d.detail === "string" ? d.detail : d.detail?.error ?? `checkout ${r.status}`);
  }
  const order = (await r.json()) as { subscription_id: string; key_id: string; label: string; amount_paise: number };
  await loadCheckoutJs();
  const ink = getComputedStyle(document.documentElement).getPropertyValue("--ink").trim() || "#141414";
  const paid = await new Promise<{ razorpay_payment_id: string; razorpay_subscription_id: string; razorpay_signature: string }>((resolve, reject) => {
    let done = false;
    const rz = new window.Razorpay!({
      key: order.key_id,
      subscription_id: order.subscription_id,
      name: "Prism",
      description: order.label,
      prefill: email ? { email } : undefined,
      theme: { color: ink },
      handler: (r: { razorpay_payment_id: string; razorpay_subscription_id: string; razorpay_signature: string }) => { done = true; resolve(r); },
      modal: { ondismiss: () => { if (!done) reject(new Error("dismissed")); } },
    });
    rz.on("payment.failed", (r: unknown) => {
      const d = (r as { error?: { description?: string } })?.error?.description ?? "That payment did not go through";
      onEvent?.("payment_failed", d);
    });
    rz.open();
  });
  const v = await fetch(`${API_URL}/api/v1/billing/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify(paid),
  });
  if (!v.ok) throw new Error(`We could not confirm the payment (ref ${paid.razorpay_payment_id}). It is recorded on Razorpay's side; write to us with that reference and we will set it right.`);
  track("Subscribe", { plan, stage: "paid" });
  return (await v.json()) as Subscribed;
}
