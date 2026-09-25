"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Close } from "@/components/icons";
import { track } from "@/lib/analytics";
import { cancelSubscription, fetchPlans, pauseSubscription, rupees, subscribe, type CancelReason, type MySubscription, type PlanOut } from "@/lib/billing";
import { billingDay } from "@/lib/dateline";
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
const when = (iso?: string | null) => (iso ? billingDay(iso) : null);

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
  const [done, setDone] = useState<{ title: string; body: string } | null>(null);
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
      setDone({ title: `Paused for ${months} ${months === 1 ? "month" : "months"}`, body: `Plus stays on until ${until ?? "the end of this month"}, then rests and comes back on ${when(r.paused_until)}. Resume sooner from this page any time.` });
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
      setDone({ title: "Cancelled", body: `Nothing more is charged; Plus stays on until ${when(r.access_until) ?? until ?? "the end of this month"}.` });
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
      setDone({ title: "Switched to yearly", body: `Yearly Plus starts ${until ?? "when this month ends"} — nothing changes until then, and nothing is charged twice.` });
      onSwitched({ plan: yearly.plan, starts_at: sub.current_period_end ?? null, price_paise: yearly.amount_paise });
    } catch (e) {
      const m = e instanceof Error ? e.message : "";
      if (m !== "dismissed") setNote(m || "Payment did not go through.");
    } finally {
      setBusy(null);
    }
  }

  const btn = "p-btn p-btn--sm max-sm:min-h-[44px]";
  const cancelAnyway = <button type="button" disabled={busy !== null} onClick={cancelNow} className={`${btn} p-btn--secondary`}>{busy === "cancel" ? "Cancelling…" : "Cancel anyway"}</button>;
  const footnote = <span style={{ font: "400 12px/1.3 var(--font-read)", color: "var(--ink-3)" }}>One click, any time · no calls, no forms</span>;

  // The Sheet (ui/Sheet): a bottom sheet on the phone, a dialog on a desk. The
  // scrim is the positioner, so the sheet never needs a transform to centre.
  return (
    <div className="p-scrim flex items-end justify-center lg:items-center lg:p-6" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="cancel-title"
        className="p-sheet p-sheet--bottom max-h-[88vh] w-full pb-[env(safe-area-inset-bottom)] lg:max-h-[85vh] lg:w-[520px] lg:rounded-[var(--r-xl)]"
      >
        <div className="p-sheet__grab lg:hidden" aria-hidden />
        <div className="flex items-center gap-2 pb-1.5 pl-5 pr-3 pt-2.5">
          <p className="min-w-0 flex-1" style={{ font: "var(--t-title-s)" }}>Cancel Plus</p>
          <button ref={closeRef} type="button" onClick={onClose} aria-label="Close" className="p-iconbtn"><Close size={16} /></button>
        </div>

        <div className="flex-1 overflow-auto px-5 pb-5 pt-1">
          {done ? (
            <div className="grid gap-2">
              <h2 id="cancel-title" className="text-balance" style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>{done.title}</h2>
              <p role="status" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{done.body}</p>
              <div className="mt-2"><button type="button" onClick={onClose} className="p-btn p-btn--secondary">Close</button></div>
            </div>
          ) : (
            <div className="grid gap-4">
              <div>
                <h2 id="cancel-title" className="text-balance" style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>Before you go</h2>
                <p className="mt-1" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
                  Cancelling stops the next charge. You keep Plus until {until ?? "the end of the month you paid for"} — nothing is taken back.
                </p>
              </div>

              <fieldset className="m-0 grid gap-1.5 border-0 p-0">
                <legend className="p-eyebrow mb-1.5">Why are you leaving? (optional)</legend>
                {REASONS.map(([k, label]) => (
                  <button key={k} type="button" onClick={() => setReason(reason === k ? null : k)} aria-pressed={reason === k} className="p-chip w-full justify-start max-sm:min-h-[44px]">{label}</button>
                ))}
                {reason === "missing-something" && (
                  <label className="mt-1 block">
                    <span className="sr-only">What was missing?</span>
                    <textarea
                      value={comment}
                      onChange={(e) => setComment(e.target.value.slice(0, 280))}
                      placeholder="What was missing? One line helps us more than you'd think."
                      rows={2}
                      className="p-input py-2.5"
                    />
                  </label>
                )}
              </fieldset>

              {offer ? (
                <div className="grid gap-3 p-3.5" style={{ border: "1px solid var(--line)", borderRadius: "var(--r-md)" }}>
                  <div className="grid min-w-0 gap-2">
                    {offer === "pause" && (
                      <>
                        <p style={{ font: "600 15px/1.3 var(--font-read)" }}>Take a break instead?</p>
                        <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
                          No charges for a while. Plus keeps running until {until ?? "the end of this month"}, then rests and comes back on its own.
                        </p>
                        <div role="radiogroup" aria-label="How long" className="p-seg justify-self-start">
                          {([1, 2, 3] as const).map((m) => (
                            <button key={m} role="radio" aria-checked={months === m} onClick={() => setMonths(m)} type="button" className="whitespace-nowrap max-sm:min-h-[44px]" style={months === m ? { background: "var(--surface)", color: "var(--ink)", boxShadow: "var(--shadow-1), 0 0 0 1px var(--line)" } : undefined}>
                              {m} {m === 1 ? "month" : "months"}
                            </button>
                          ))}
                        </div>
                      </>
                    )}
                    {offer === "yearly" && yearly && (
                      <>
                        <p style={{ font: "600 15px/1.3 var(--font-read)" }}>Yearly is {rupees(perMonth)} a month</p>
                        <ul className="grid gap-1.5">
                          {[
                            `${rupees(yearly.amount_paise)} a year${saving ? ` — ${rupees(saving)} less than twelve months` : ""}`,
                            `Starts ${until ?? "when this month ends"}; nothing changes today, nothing is charged twice`,
                            "Seven days from any yearly charge to take it all back",
                          ].map((line) => (
                            <li key={line} className="grid grid-cols-[18px_minmax(0,1fr)] gap-2" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
                              <span className="mt-[5px]" aria-hidden><Check size={14} /></span>
                              <span>{line}</span>
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                  {/* The one offer and the exit on the same row, at the same size. */}
                  <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
                    {offer === "pause" && (
                      <button type="button" disabled={busy !== null} onClick={pause} className={`${btn} p-btn--primary`}>{busy === "pause" ? "Pausing…" : `Pause for ${months} ${months === 1 ? "month" : "months"}`}</button>
                    )}
                    {offer === "yearly" && yearly && (
                      <button type="button" disabled={busy !== null} onClick={switchToYearly} className={`${btn} p-btn--primary`}>{busy === "switch" ? "Opening…" : `Switch to yearly · ${rupees(yearly.amount_paise)}`}</button>
                    )}
                    {cancelAnyway}
                    <span className="basis-full sm:ml-auto sm:basis-auto">{footnote}</span>
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap items-center justify-end gap-x-2.5 gap-y-1">{footnote}{cancelAnyway}</div>
              )}
              {note && <p role="status" style={{ font: "500 13.5px/1.45 var(--font-read)", color: "var(--danger)" }}>{note}</p>}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
