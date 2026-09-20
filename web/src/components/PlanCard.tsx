"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CancelSheet } from "@/components/CancelSheet";
import { cancelSubscription, fetchMySubscription, refundSubscription, resumeSubscription, rupees, type MySubscription } from "@/lib/billing";
import type { Session } from "@/lib/session";

// The subscription as the reader sees it, every state of its life
// (DESIGN.md § Account): free · active (renews) · ending (no more charges) ·
// paused (rests, then returns on its own) · past_due (a charge failed; access
// to the grace date) · halted · refunded · lapsed. One line and one action per
// state. Cancelling a monthly plan opens the cancel sheet (one screen: the
// truth, an optional reason, one offer, "Cancel anyway" beside it); a yearly
// plan confirms inline, and while the Refund policy's seven days are open the
// same card offers the refund the same way. Razorpay emails the receipts;
// the Payments list below the card links every invoice.
export const PLAN_LABEL: Record<string, string> = { plus_monthly: "Plus · monthly", plus_yearly: "Plus · yearly", founding: "Founding member" };
const when = (iso?: string | null) => (iso ? new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : null);

export function planState(sub: MySubscription | null) {
  if (!sub || !sub.status || sub.plan === "free") return "free" as const;
  if (sub.refund_id) return "refunded" as const;
  if (sub.status === "paused") return "paused" as const;
  if (sub.status === "past_due") return "past_due" as const;
  if (sub.status === "halted") return "halted" as const;
  if (sub.status === "active" && sub.cancel_at) return "ending" as const;
  if (sub.status === "active") return "active" as const;
  return "lapsed" as const; // cancelled and past its date, expired
}

/** The refund is offered only while the policy's window is open. */
export function refundOpen(sub: MySubscription | null, now = Date.now()) {
  return Boolean(sub?.refundable_until && !sub.refund_id && new Date(sub.refundable_until).getTime() > now);
}

export function PlanCard({ session, compact = false }: { session: Session; compact?: boolean }) {
  const [sub, setSub] = useState<MySubscription | null | undefined>(undefined);
  const [confirm, setConfirm] = useState<"cancel" | "refund" | null>(null);
  const [sheet, setSheet] = useState(false);
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
  const monthly = sub?.plan === "plus_monthly";
  const canRefund = state === "active" && refundOpen(sub);

  async function run(action: () => Promise<void>, failure: string) {
    setBusy(true);
    setNote(null);
    try {
      await action();
      setConfirm(null);
    } catch {
      setNote(failure);
    } finally {
      setBusy(false);
    }
  }
  const stop = () =>
    run(async () => {
      const r = await cancelSubscription(session.token);
      setSub({ ...sub!, cancel_at: r.access_until ?? new Date().toISOString() });
    }, "We could not reach the payment provider. Try again in a minute, or write to us.");
  const refund = () =>
    run(async () => {
      const r = await refundSubscription(session.token);
      setSub({ ...sub!, status: "cancelled", refund_id: r.refund_id, cancel_at: r.ended_at, current_period_end: r.ended_at, refundable_until: null });
    }, "The refund could not be made just now. Try again in a minute, or write to us with the payment reference from your receipt.");
  const resume = () =>
    run(async () => {
      await resumeSubscription(session.token);
      setSub(await fetchMySubscription(session.token));
    }, "We could not reach the payment provider. Try again in a minute.");

  const headline = { free: "Free", active: label, ending: label, paused: label, past_due: label, halted: label, refunded: "Free", lapsed: "Free" }[state];
  const line = {
    free: "Every record, source, quote and clip. 10 questions a day.",
    active: sub?.current_period_end ? `Renews ${when(sub.current_period_end)}` : "Active",
    ending: sub?.next
      ? `Ends ${when(sub.cancel_at)} · then ${PLAN_LABEL[sub.next.plan] ?? "Plus"} from ${when(sub.next.starts_at) ?? "that day"}`
      : `Ends ${when(sub?.cancel_at) ?? "at the end of this period"} · no further charges`,
    paused: `Paused · Plus stays on until ${when(sub?.current_period_end) ?? "the end of this month"} · resumes ${when(sub?.paused_until) ?? "later"} on its own`,
    past_due: `The last charge did not go through · Plus stays on until ${when(sub?.current_period_end) ?? "the grace period ends"} while Razorpay retries`,
    halted: "Paused after repeated failed charges · reading stays free",
    refunded: `Refunded${sub?.price_paise ? ` ${rupees(sub.price_paise)}` : ""} · Plus ended${sub?.cancel_at ? ` on ${when(sub.cancel_at)}` : ""} · reaches your bank in 5–7 working days`,
    lapsed: `Your Plus ended${sub?.current_period_end ? ` on ${when(sub.current_period_end)}` : ""}.`,
  }[state];
  const showPrice = !["free", "lapsed", "refunded"].includes(state) && sub?.price_paise;

  return (
    <div className={compact ? "px-4 py-4" : "card p-5"} aria-label="Your plan">
      <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
        <div className="min-w-0 flex-1">
          {!compact && <p className="text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>Plan</p>}
          <p className={`${compact ? "text-[15px]" : "mt-1 text-[18px]"} font-semibold`}>
            {headline}
            {showPrice ? <span className="ml-2 font-mono text-[12px] font-normal" style={{ color: "var(--ink-3)" }}>{rupees(sub!.price_paise!)}</span> : null}
          </p>
          <p className="mt-0.5 text-[13.5px] leading-[1.5]" style={{ color: state === "past_due" ? "var(--ink)" : "var(--ink-3)" }}>{line}</p>
          {canRefund && (
            <p className="mt-0.5 font-mono text-[11px] uppercase tracking-[0.03em]" style={{ color: "var(--ink-3)" }}>Full refund open until {when(sub?.refundable_until)}</p>
          )}
        </div>
        {(state === "free" || state === "lapsed" || state === "refunded") && <Link href="/plus?from=account" className="btn btn-primary btn-sm">Get Plus</Link>}
        {state === "past_due" && <span className="font-mono text-[11px] uppercase tracking-[0.03em]" style={{ color: "var(--ink-3)" }}>Check your email</span>}
        {state === "paused" && <button type="button" disabled={busy} onClick={resume} className="btn btn-secondary btn-sm">{busy ? "Resuming…" : "Resume now"}</button>}
        {state === "active" && !confirm && (
          <span className="flex items-center gap-1">
            {canRefund && <button type="button" onClick={() => setConfirm("refund")} className="btn btn-ghost btn-sm" style={{ color: "var(--ink-2)" }}>Refund</button>}
            <button type="button" onClick={() => (monthly ? setSheet(true) : setConfirm("cancel"))} className="btn btn-ghost btn-sm" style={{ color: "var(--ink-2)" }}>Cancel</button>
          </span>
        )}
      </div>
      {confirm === "cancel" && (
        <div className="mt-3 flex flex-wrap items-center gap-3 border-t pt-3 text-[13.5px]" style={{ borderColor: "var(--line)" }}>
          <span style={{ color: "var(--ink-2)" }}>Stop the next charge? You keep Plus until {when(sub?.current_period_end) ?? "the period ends"}.</span>
          <button type="button" disabled={busy} onClick={stop} className="btn btn-secondary btn-sm">{busy ? "Stopping…" : "Yes, cancel"}</button>
          <button type="button" onClick={() => setConfirm(null)} className="btn btn-ghost btn-sm">Keep Plus</button>
        </div>
      )}
      {confirm === "refund" && (
        <div className="mt-3 flex flex-wrap items-center gap-3 border-t pt-3 text-[13.5px]" style={{ borderColor: "var(--line)" }}>
          <span style={{ color: "var(--ink-2)" }}>
            Refund {sub?.price_paise ? rupees(sub.price_paise) : "this charge"} in full to the method you paid with? Plus ends now; the money shows in 5–7 working days.
          </span>
          <button type="button" disabled={busy} onClick={refund} className="btn btn-secondary btn-sm">{busy ? "Refunding…" : "Yes, refund"}</button>
          <button type="button" onClick={() => setConfirm(null)} className="btn btn-ghost btn-sm">Keep Plus</button>
        </div>
      )}
      {note && <p className="mt-2 text-[13px]" role="status" style={{ color: "var(--danger)" }}>{note}</p>}
      {!compact && state !== "free" && (
        <p className="mt-3 border-t pt-3 text-[12.5px] leading-[1.5]" style={{ borderColor: "var(--line)", color: "var(--ink-3)" }}>
          Receipts: Razorpay emails one for every charge to {session.email}; each is also under Payments below. Questions about a charge: <Link href="/refunds" className="underline underline-offset-[3px]">Refund policy</Link>.
        </p>
      )}
      {sub && (
        <CancelSheet
          open={sheet}
          onClose={() => setSheet(false)}
          session={session}
          sub={sub}
          onPaused={(until) => setSub({ ...sub, status: "paused", paused_until: until })}
          onCancelled={(accessUntil) => setSub({ ...sub, cancel_at: accessUntil ?? new Date().toISOString() })}
          onSwitched={(next) => setSub({ ...sub, cancel_at: sub.current_period_end ?? new Date().toISOString(), next })}
        />
      )}
    </div>
  );
}
