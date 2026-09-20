"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Close } from "@/components/icons";
import { track } from "@/lib/analytics";
import { cancelSubscription, fetchPlans, pauseSubscription, rupees, subscribe, type CancelReason, type MySubscription, type PlanOut } from "@/lib/billing";
import type { Session } from "@/lib/session";

/**
 * The cancel sheet for a renewing monthly plan (DESIGN.md § Account). One
 * screen, and the truth first: cancelling stops the next charge and Plus runs
 * to the end of the paid month. Then an optional reason, ONE offer matched to
 * it — a pause (1–3 months, comes back on its own) when the reader is not
 * using it, the yearly saving when it is the price — and "Cancel anyway" on
 * the same row at the same size. Never a second offer, never a hidden exit:
 * India's dark-pattern guidelines (CCPA 2023) name the "subscription trap",
 * and the pattern the data favours is the pause anyway (a quarter of
 * would-be churners take it; most come back).
 */
const REASONS: [CancelReason, string][] = [
  ["not-using", "Not using it enough"],
  ["too-expensive", "Too expensive"],
  ["missing-something", "Missing something"],
  ["other", "Something else"],
];
const when = (iso?: string | null) => (iso ? new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : null);

export function CancelSheet({
  open,
  onClose,
  session,
  sub,
  onPaused,
  onCancelled,
  onSwitched,
}: {
  open: boolean;
  onClose: () => void;
  session: Session;
  sub: MySubscription;
  onPaused: (pausedUntil: string) => void;
  onCancelled: (accessUntil: string | null) => void;
  onSwitched: (nextPlan: { plan: string; starts_at: string | null; price_paise: number | null }) => void;
}) {
  const [reason, setReason] = useState<CancelReason | null>(null);
  const [comment, setComment] = useState("");
  const [months, setMonths] = useState<1 | 2 | 3>(2);
  const [yearly, setYearly] = useState<PlanOut | null | undefined>(undefined);
  const [monthly, setMonthly] = useState<PlanOut | null>(null);
  const [busy, setBusy] = useState<"pause" | "cancel" | "switch" | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [pauseGone, setPauseGone] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    track("Subscribe", { stage: "cancel-sheet" });
    setReason(null); setComment(""); setNote(null); setDone(null); setPauseGone(false);
    fetchPlans()
      .then((p) => { setYearly(p.plans.find((x) => x.plan === "plus_yearly") ?? null); setMonthly(p.plans.find((x) => x.plan === "plus_monthly") ?? null); })
      .catch(() => setYearly(null));
    closeRef.current?.focus({ preventScroll: true });
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!open) return null;
  const until = when(sub.current_period_end);
  const offer: "pause" | "yearly" | null =
    reason === "too-expensive" ? (yearly ? "yearly" : null) : reason === "missing-something" ? null : pauseGone ? null : "pause";
  const perMonth = yearly ? Math.round(yearly.amount_paise / 12) : 0;
  const saving = yearly && (monthly ?? { amount_paise: sub.price_paise ?? 0 }) ? Math.max(0, (monthly?.amount_paise ?? sub.price_paise ?? 0) * 12 - yearly.amount_paise) : 0;

  async function pause() {
    setBusy("pause"); setNote(null);
    try {
      const r = await pauseSubscription(session.token, months);
      track("Subscribe", { stage: "paused", months });
      setDone(`Paused. Plus stays on until ${until ?? "the end of this month"}, then rests and comes back on ${when(r.paused_until)}. Resume sooner from this page any time.`);
      onPaused(r.paused_until);
    } catch (e) {
      if (e instanceof Error && e.message === "unavailable") {
        setPauseGone(true);
        setNote("Pausing is not available on this plan yet. You can still cancel below.");
      } else {
        setNote("We could not reach the payment provider. Try again in a minute.");
      }
    } finally {
      setBusy(null);
    }
  }

  async function cancelNow() {
    setBusy("cancel"); setNote(null);
    try {
      const r = await cancelSubscription(session.token, { reason: reason ?? undefined, comment: comment || undefined });
      track("Subscribe", { stage: "cancelled", reason: reason ?? "none" });
      setDone(`Done. Nothing more is charged; Plus stays on until ${when(r.access_until) ?? until ?? "the end of this month"}.`);
      onCancelled(r.access_until);
    } catch {
      setNote("We could not reach the payment provider. Try again in a minute, or write to us.");
    } finally {
      setBusy(null);
    }
  }

  async function switchToYearly() {
    if (!yearly) return;
    setBusy("switch"); setNote(null);
    try {
      await subscribe(yearly.plan, session.token, session.email, (_k, d) => setNote(`${d}. The sheet is still open — try UPI or another card.`), { startAfterCurrent: true });
      track("Subscribe", { stage: "switched-yearly" });
      setDone(`Yearly Plus starts ${until ?? "when this month ends"} — nothing changes until then, and nothing is charged twice.`);
      onSwitched({ plan: yearly.plan, starts_at: sub.current_period_end ?? null, price_paise: yearly.amount_paise });
    } catch (e) {
      const m = e instanceof Error ? e.message : "";
      if (m !== "dismissed") setNote(m || "Payment did not go through.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-[60]" style={{ background: "rgba(20,22,19,.35)" }} onClick={onClose} aria-hidden />
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="cancel-title"
        className="upgrade-sheet fixed inset-x-0 bottom-0 z-[61] flex max-h-[88vh] flex-col overflow-y-auto rounded-t-[16px] border-t p-5 pb-[calc(env(safe-area-inset-bottom)+20px)] lg:inset-auto lg:left-1/2 lg:top-1/2 lg:w-[460px] lg:-translate-x-1/2 lg:-translate-y-1/2 lg:rounded-[16px] lg:border lg:p-6"
        style={{ background: "var(--bg-elevated)", borderColor: "var(--line-strong)", boxShadow: "var(--shadow-2)" }}
      >
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <p className="meta-line"><span>Plus · monthly</span>{until && <><span className="dot" /><span>renews {until}</span></>}</p>
            <h2 id="cancel-title" className="font-record mt-2 text-[26px] font-medium leading-[1.15] tracking-[-0.01em] text-balance">{done ? "Done" : "Before you go"}</h2>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} aria-label="Close" className="grid h-10 w-10 flex-none place-items-center rounded-full border" style={{ borderColor: "var(--line)", color: "var(--ink)" }}>
            <Close />
          </button>
        </div>

        {done ? (
          <>
            <p className="mt-4 text-[15px] leading-[1.6]" role="status">{done}</p>
            <div className="mt-5"><button type="button" onClick={onClose} className="btn btn-secondary">Close</button></div>
          </>
        ) : (
          <>
            <p className="mt-3 text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
              Cancelling stops the next charge. You keep Plus until {until ?? "the end of the month you paid for"} — nothing is taken back.
            </p>

            <p className="mt-5 text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>Why are you leaving? <span className="font-normal normal-case tracking-normal">(optional)</span></p>
            <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label="Reason">
              {REASONS.map(([k, label]) => (
                <button key={k} type="button" onClick={() => setReason(reason === k ? null : k)} aria-pressed={reason === k} className="chip h-8 px-3 text-[13px]">{label}</button>
              ))}
            </div>
            {reason === "missing-something" && (
              <label className="mt-3 block">
                <span className="sr-only">What was missing?</span>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value.slice(0, 280))}
                  placeholder="What was missing? One line helps us more than you'd think."
                  rows={2}
                  className="w-full rounded-[10px] border px-3 py-2 text-[16px] leading-[1.5]"
                  style={{ borderColor: "var(--line-strong)", background: "var(--surface)", color: "var(--ink)" }}
                />
              </label>
            )}

            {offer === "pause" && (
              <div className="mt-5 border-t pt-4" style={{ borderColor: "var(--line)" }}>
                <p className="text-[16px] font-semibold">Take a break instead?</p>
                <p className="mt-1 text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
                  No charges for a while. Plus keeps running until {until ?? "the end of this month"}, then rests and comes back on its own.
                </p>
                <div role="radiogroup" aria-label="How long" className="seg mt-3 inline-flex">
                  {([1, 2, 3] as const).map((m) => (
                    <button key={m} role="radio" aria-checked={months === m} onClick={() => setMonths(m)} type="button">{m} {m === 1 ? "month" : "months"}</button>
                  ))}
                </div>
              </div>
            )}
            {offer === "yearly" && yearly && (
              <div className="mt-5 border-t pt-4" style={{ borderColor: "var(--line)" }}>
                <p className="text-[16px] font-semibold">Yearly is {rupees(perMonth)} a month</p>
                <ul className="mt-2 flex flex-col">
                  {[
                    `${rupees(yearly.amount_paise)} a year${saving ? ` — ${rupees(saving)} less than twelve months` : ""}`,
                    `Starts ${until ?? "when this month ends"}; nothing changes today, nothing is charged twice`,
                    "Seven days from any yearly charge to take it all back",
                  ].map((line) => (
                    <li key={line} className="flex items-start gap-2.5 border-t py-2 text-[14.5px] leading-[1.5]" style={{ borderColor: "var(--line)" }}>
                      <span className="mt-[3px] shrink-0" aria-hidden><Check size={16} /></span>
                      <span>{line}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-5 flex flex-wrap items-center gap-3">
              {offer === "pause" && (
                <button type="button" disabled={busy !== null} onClick={pause} className="btn btn-primary">{busy === "pause" ? "Pausing…" : `Pause for ${months} ${months === 1 ? "month" : "months"}`}</button>
              )}
              {offer === "yearly" && yearly && (
                <button type="button" disabled={busy !== null} onClick={switchToYearly} className="btn btn-primary">{busy === "switch" ? "Opening…" : `Switch to yearly · ${rupees(yearly.amount_paise)}`}</button>
              )}
              <button type="button" disabled={busy !== null} onClick={cancelNow} className="btn btn-secondary">{busy === "cancel" ? "Cancelling…" : "Cancel anyway"}</button>
            </div>
            {note && <p className="mt-3 text-[13px]" role="status" style={{ color: "var(--danger)" }}>{note}</p>}
            <p className="mt-4 font-mono text-[11px] uppercase tracking-[0.03em]" style={{ color: "var(--ink-3)" }}>One click, any time · no calls, no forms</p>
          </>
        )}
      </section>
    </>
  );
}
