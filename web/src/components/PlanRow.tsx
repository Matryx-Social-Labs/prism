"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { cancelSubscription, fetchMySubscription, rupees, type MySubscription } from "@/lib/billing";
import type { Session } from "@/lib/session";

// The account page's plan line: what you are on, when it renews, and the one
// click that stops it (BUSINESS-MODEL.md §8: cancellation must be one click —
// it is also what makes the first charge easy to accept). Access runs to the
// end of the paid period either way.
export function PlanRow({ session }: { session: Session }) {
  const [sub, setSub] = useState<MySubscription | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    fetchMySubscription(session.token).then(setSub).catch(() => setSub({ plan: "free" }));
  }, [session.token]);
  if (!sub) return null;
  const on = sub.status === "active" || sub.status === "past_due";
  const when = (iso?: string | null) => (iso ? new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : null);
  const label = sub.plan === "founding" ? "Founding member" : sub.plan === "plus_yearly" ? "Plus · yearly" : sub.plan === "plus_monthly" ? "Plus · monthly" : "Free";

  async function stop() {
    setBusy(true);
    try {
      const r = await cancelSubscription(session.token);
      setSub({ ...sub!, cancel_at: r.access_until ?? new Date().toISOString() });
      setConfirm(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-[56px] flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3" style={{ borderColor: "var(--line)" }}>
      <div className="min-w-0 flex-1">
        <p className="text-[15px]">
          Plan <b className="font-semibold">{on ? label : "Free"}</b>
          {on && sub.price_paise ? <span className="ml-2 font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>{rupees(sub.price_paise)}</span> : null}
        </p>
        {on && (
          <p className="text-[13px]" style={{ color: "var(--ink-3)" }}>
            {sub.cancel_at ? `Ends ${when(sub.cancel_at) ?? "at the end of this period"} · no further charges` : sub.status === "past_due" ? `Last charge failed · access until ${when(sub.current_period_end) ?? "the grace period ends"}` : sub.current_period_end ? `Renews ${when(sub.current_period_end)}` : "Active"}
          </p>
        )}
      </div>
      {!on && <Link href="/plus" className="text-[14px] font-semibold underline-offset-4 hover:underline" style={{ color: "var(--accent)" }}>Plus →</Link>}
      {on && !sub.cancel_at && !confirm && (
        <button type="button" onClick={() => setConfirm(true)} className="text-[14px] font-semibold underline-offset-4 hover:underline" style={{ color: "var(--ink-2)" }}>Cancel</button>
      )}
      {confirm && (
        <span className="flex items-center gap-3 text-[13.5px]">
          <span style={{ color: "var(--ink-2)" }}>Stop the next charge? You keep Plus until {when(sub.current_period_end) ?? "the period ends"}.</span>
          <button type="button" disabled={busy} onClick={stop} className="btn btn-secondary btn-sm">{busy ? "Stopping…" : "Yes, cancel"}</button>
          <button type="button" onClick={() => setConfirm(false)} className="btn btn-ghost btn-sm">Keep</button>
        </span>
      )}
    </div>
  );
}
