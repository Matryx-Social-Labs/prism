"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { cancelSubscription, fetchMySubscription, rupees, type MySubscription } from "@/lib/billing";
import type { Session } from "@/lib/session";

// The subscription as the reader sees it, every state of its life
// (DESIGN.md § Account): free · active (renews) · cancelled (ends, no more
// charges) · past_due (a charge failed; access to the grace date) · halted
// · paid up with no renewal to come. One action per state, and cancelling is
// one click plus one confirmation, with the date access runs to said out
// loud (BUSINESS-MODEL.md §8). Razorpay emails the receipts; we say so.
export const PLAN_LABEL: Record<string, string> = { plus_monthly: "Plus · monthly", plus_yearly: "Plus · yearly", founding: "Founding member" };
const when = (iso?: string | null) => (iso ? new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : null);

export function planState(sub: MySubscription | null) {
  if (!sub || !sub.status || sub.plan === "free") return "free" as const;
  if (sub.status === "past_due") return "past_due" as const;
  if (sub.status === "halted") return "halted" as const;
  if (sub.status === "active" && sub.cancel_at) return "ending" as const;
  if (sub.status === "active") return "active" as const;
  return "lapsed" as const; // cancelled and past its date, expired
}

export function PlanCard({ session, compact = false }: { session: Session; compact?: boolean }) {
  const [sub, setSub] = useState<MySubscription | null | undefined>(undefined);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  useEffect(() => {
    fetchMySubscription(session.token).then(setSub).catch(() => setSub({ plan: "free" }));
  }, [session.token]);

  if (sub === undefined) {
    return <div className={compact ? "px-4 py-4" : "card p-5"}><span className="pulse-skel block h-5 w-40 rounded" style={{ background: "var(--sunken)" }} aria-label="Loading your plan" /></div>;
  }
  const state = planState(sub);
  const label = PLAN_LABEL[sub?.plan ?? ""] ?? "Plus";

  async function stop() {
    setBusy(true);
    setNote(null);
    try {
      const r = await cancelSubscription(session.token);
      setSub({ ...sub!, cancel_at: r.access_until ?? new Date().toISOString() });
      setConfirm(false);
    } catch {
      setNote("We could not reach the payment provider. Try again in a minute, or write to us.");
    } finally {
      setBusy(false);
    }
  }

  const headline = {
    free: "Free",
    active: label,
    ending: label,
    past_due: label,
    halted: label,
    lapsed: "Free",
  }[state];
  const line = {
    free: "Every record, source, quote and clip. 10 questions a day.",
    active: sub?.current_period_end ? `Renews ${when(sub.current_period_end)}` : "Active",
    ending: `Ends ${when(sub?.cancel_at) ?? "at the end of this period"} · no further charges`,
    past_due: `The last charge did not go through · Plus stays on until ${when(sub?.current_period_end) ?? "the grace period ends"} while Razorpay retries`,
    halted: "Paused after repeated failed charges · reading stays free",
    lapsed: `Your Plus ended${sub?.current_period_end ? ` on ${when(sub.current_period_end)}` : ""}.`,
  }[state];

  return (
    <div className={compact ? "px-4 py-4" : "card p-5"} aria-label="Your plan">
      <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
        <div className="min-w-0 flex-1">
          {!compact && <p className="text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>Plan</p>}
          <p className={`${compact ? "text-[15px]" : "mt-1 text-[18px]"} font-semibold`}>
            {headline}
            {state !== "free" && state !== "lapsed" && sub?.price_paise ? <span className="ml-2 font-mono text-[12px] font-normal" style={{ color: "var(--ink-3)" }}>{rupees(sub.price_paise)}</span> : null}
          </p>
          <p className="mt-0.5 text-[13.5px] leading-[1.5]" style={{ color: state === "past_due" ? "var(--ink)" : "var(--ink-3)" }}>{line}</p>
        </div>
        {(state === "free" || state === "lapsed") && <Link href="/plus?from=account" className="btn btn-primary btn-sm">Get Plus</Link>}
        {state === "past_due" && <span className="font-mono text-[11px] uppercase tracking-[0.03em]" style={{ color: "var(--ink-3)" }}>Check your email</span>}
        {(state === "active") && !confirm && (
          <button type="button" onClick={() => setConfirm(true)} className="btn btn-ghost btn-sm" style={{ color: "var(--ink-2)" }}>Cancel</button>
        )}
      </div>
      {confirm && (
        <div className="mt-3 flex flex-wrap items-center gap-3 border-t pt-3 text-[13.5px]" style={{ borderColor: "var(--line)" }}>
          <span style={{ color: "var(--ink-2)" }}>Stop the next charge? You keep Plus until {when(sub?.current_period_end) ?? "the period ends"}.</span>
          <button type="button" disabled={busy} onClick={stop} className="btn btn-secondary btn-sm">{busy ? "Stopping…" : "Yes, cancel"}</button>
          <button type="button" onClick={() => setConfirm(false)} className="btn btn-ghost btn-sm">Keep Plus</button>
        </div>
      )}
      {note && <p className="mt-2 text-[13px]" role="status" style={{ color: "var(--danger)" }}>{note}</p>}
      {!compact && state !== "free" && (
        <p className="mt-3 border-t pt-3 text-[12.5px] leading-[1.5]" style={{ borderColor: "var(--line)", color: "var(--ink-3)" }}>
          Receipts: Razorpay emails one for every charge to {session.email}. Questions about a charge: <Link href="/refunds" className="underline underline-offset-[3px]">Refund policy</Link>.
        </p>
      )}
    </div>
  );
}
