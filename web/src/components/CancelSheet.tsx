"use client";

import { useEffect, useRef, useState } from "react";
import { Close } from "@/components/icons";
import { Alert } from "@/components/ui";
import { track } from "@/lib/analytics";
import { cancelSubscription, fetchPlans, pauseSubscription, rupees, subscribe, type CancelReason, type MySubscription, type PlanOut } from "@/lib/billing";
import { billingDay } from "@/lib/dateline";
import type { Session } from "@/lib/session";

/**
 * The cancel sheet for a renewing monthly plan (Design System v2 ·
 * money/CancelSheetBody). One screen, the truth first: cancelling stops the
 * next charge and Plus runs to the end of the paid month. Then an optional
 * reason, and once one is given, ONE offer matched to it — the yearly plan
 * when it is the price, a 1–3 month pause otherwise — with "Cancel anyway"
 * in the same box. Never a second offer, never a hidden exit: India's
 * dark-pattern guidelines (CCPA 2023) name the "subscription trap".
 * Each offer is the backend's own: POST /billing/pause (409 when Razorpay has
 * not enabled pausing — the sheet then drops it) and a yearly checkout with
 * start_after_current (a new subscription from the day the month ends; UPI and
 * e-mandate plans cannot be changed in place).
 */
const REASONS: [CancelReason, string][] = [
  ["not-using", "Not using it enough"],
  ["too-expensive", "Too expensive"],
  ["missing-something", "Missing something"],
  ["other", "Something else"],
];
const MONTHS = [1, 2, 3] as const;
// api/routes/billing.pause: paused_until = the paid period's end + 30 days a month.
const PAUSE_DAY_MS = 30 * 24 * 3600 * 1000;
const COMMENT_MAX = 140;
const when = (iso?: string | null) => (iso ? billingDay(iso) : null);
const monthsLabel = (m: number) => `${m} ${m === 1 ? "month" : "months"}`;

/** An action that failed, in words: Razorpay's 502 means nothing changed on either side. */
export function couldNot(verb: string, e: unknown): string {
  return /\b502\b/.test(e instanceof Error ? e.message : "")
    ? `Couldn't ${verb}: Razorpay did not answer and nothing changed. Try again in a minute.`
    : `Couldn't ${verb} just now. Try again in a minute, or write to us.`;
}

type Done = { kind: "pause" | "cancel" | "switch"; until: string | null; back?: string | null; price?: number };

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
  const [months, setMonths] = useState<1 | 2 | 3 | null>(null);
  const [yearly, setYearly] = useState<PlanOut | null>(null);
  const [monthly, setMonthly] = useState<PlanOut | null>(null);
  const [busy, setBusy] = useState<"pause" | "cancel" | "switch" | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [declined, setDeclined] = useState<string | null>(null);
  const [pauseGone, setPauseGone] = useState(false);
  const [done, setDone] = useState<Done | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    track("Subscribe", { stage: "cancel-sheet" });
    setReason(null); setComment(""); setMonths(null); setNote(null); setDeclined(null); setDone(null); setPauseGone(false);
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
  const offer: "pause" | "yearly" | null = !reason
    ? null
    : reason === "too-expensive" && yearly
      ? "yearly"
      : pauseGone
        ? null
        : "pause";
  const monthlyPaise = monthly?.amount_paise ?? sub.price_paise ?? 0;
  const saving = yearly ? Math.max(0, monthlyPaise * 12 - yearly.amount_paise) : 0;
  const pauseBase = sub.current_period_end ? Date.parse(sub.current_period_end) : Date.now();
  const resumes = months ? when(new Date(pauseBase + months * PAUSE_DAY_MS).toISOString()) : null;

  async function pause() {
    if (!months) return;
    setBusy("pause"); setNote(null);
    try {
      const r = await pauseSubscription(session.token, months);
      track("Subscribe", { stage: "paused", months });
      setDone({ kind: "pause", until: r.paid_until ?? sub.current_period_end ?? null, back: r.paused_until });
      onPaused(r.paused_until);
    } catch (e) {
      if (e instanceof Error && e.message === "unavailable") {
        setPauseGone(true);
        setNote("Pausing is not available on this plan yet. You can still cancel below.");
      } else {
        setNote(couldNot("pause", e));
      }
    } finally {
      setBusy(null);
    }
  }

  async function cancelNow() {
    setBusy("cancel"); setNote(null);
    try {
      const r = await cancelSubscription(session.token, { reason: reason ?? undefined, comment: comment.trim() || undefined });
      track("Subscribe", { stage: "cancelled", reason: reason ?? "none" });
      setDone({ kind: "cancel", until: r.access_until ?? sub.current_period_end ?? null });
      onCancelled(r.access_until);
    } catch (e) {
      setNote(couldNot("cancel", e));
    } finally {
      setBusy(null);
    }
  }

  async function switchToYearly() {
    if (!yearly) return;
    setBusy("switch"); setNote(null); setDeclined(null);
    try {
      await subscribe(yearly.plan, session.token, session.email, (_k, d) => setDeclined(d), { startAfterCurrent: true });
      track("Subscribe", { stage: "switched-yearly" });
      setDone({ kind: "switch", until: sub.current_period_end ?? null, price: yearly.amount_paise });
      onSwitched({ plan: yearly.plan, starts_at: sub.current_period_end ?? null, price_paise: yearly.amount_paise });
    } catch (e) {
      const m = e instanceof Error ? e.message : "";
      if (m !== "dismissed") setNote(m || "The payment did not go through. Nothing was charged.");
    } finally {
      setBusy(null);
    }
  }

  const btn = "p-btn p-btn--sm max-sm:min-h-[44px]";
  const small = { font: "400 12px/1.35 var(--font-read)", color: "var(--ink-3)" } as const;
  const title = { font: "var(--t-display-m)", letterSpacing: "var(--track-display)" } as const;
  const footnote = <span style={small}>One click, any time · no calls, no forms</span>;
  const cancelAnyway = (variant: "ghost" | "secondary") => (
    <button type="button" disabled={busy !== null} onClick={cancelNow} className={`${btn} p-btn--${variant}`}>{busy === "cancel" ? "Cancelling…" : "Cancel anyway"}</button>
  );

  const doneCopy = done && {
    pause: ["Plus is paused", `Plus stays on until ${when(done.until) ?? "the end of this month"}, then pauses. Nothing is charged until it resumes on ${when(done.back) ?? "the day you chose"}. You can resume sooner from your account.`],
    cancel: [`Plus will end on ${when(done.until) ?? "the last day you paid for"}`, "No further charges. You keep Plus until then."],
    switch: [
      `Yearly starts ${when(done.until) ?? "when this month ends"}`,
      `${done.price ? rupees(done.price) : "The yearly price"} is charged on ${when(done.until) ?? "that day"}, once. Nothing is charged twice, and the 7-day full refund starts from that charge.`,
    ],
  }[done.kind];

  // A bottom sheet on the phone, a 480px dialog on a desk. The scrim is the
  // positioner, so the sheet never needs a transform to centre.
  return (
    <div className="p-scrim flex items-end justify-center lg:items-center lg:p-6" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="cancel-title"
        className="p-sheet p-sheet--bottom max-h-[88vh] w-full pb-[env(safe-area-inset-bottom)] lg:max-h-[85vh] lg:w-[480px] lg:rounded-[var(--r-xl)]"
      >
        <div className="p-sheet__grab lg:hidden" aria-hidden />
        <div className="flex justify-end px-3 pt-2.5">
          <button ref={closeRef} type="button" onClick={onClose} aria-label="Close" className="p-iconbtn"><Close size={16} /></button>
        </div>

        <div className="flex-1 overflow-auto px-5 pb-5">
          {doneCopy ? (
            <div className="grid gap-2.5" role="status">
              <h2 id="cancel-title" className="text-balance" style={title}>{doneCopy[0]}</h2>
              <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{doneCopy[1]}</p>
              <p className="p-mono uppercase" style={{ fontSize: 11, color: "var(--ink-3)" }}>An email confirming this is on its way</p>
              <div><button type="button" onClick={onClose} className="p-btn p-btn--secondary">Close</button></div>
            </div>
          ) : (
            <div className="grid gap-4">
              <div>
                <h2 id="cancel-title" className="text-balance" style={title}>Before you go</h2>
                <p className="mt-1" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
                  You keep Plus until {until ?? "the end of the month you paid for"}. Paid time is never taken back.
                </p>
              </div>

              {declined && (
                <Alert tone="error" title="The payment did not go through">
                  {declined}. Nothing was charged; Razorpay&rsquo;s sheet is still open — try UPI or another card.
                </Alert>
              )}

              <fieldset className="m-0 grid gap-1.5 border-0 p-0">
                <legend className="p-eyebrow mb-1.5">Why are you leaving? (optional)</legend>
                {REASONS.map(([k, label]) => (
                  <button key={k} type="button" onClick={() => setReason(reason === k ? null : k)} aria-pressed={reason === k} className="p-chip min-h-[44px] w-full justify-start">{label}</button>
                ))}
                {reason === "missing-something" && (
                  <label className="mt-1 block">
                    <span className="sr-only">What&rsquo;s missing?</span>
                    <input value={comment} onChange={(e) => setComment(e.target.value)} maxLength={COMMENT_MAX} placeholder="What's missing? One line is enough" className="p-input" />
                  </label>
                )}
              </fieldset>

              {offer ? (
                <div className="grid gap-3.5 p-3.5" style={{ border: "1px solid var(--line-strong)", borderRadius: "var(--r-md)" }}>
                  {offer === "yearly" && yearly && (
                    <div className="grid min-w-0 gap-1.5">
                      <p style={{ font: "600 15px/1.3 var(--font-read)" }}>Switch to yearly · {rupees(yearly.amount_paise)}</p>
                      <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
                        {saving > 0 && <>Save {rupees(saving)} a year against monthly. </>}Starts {until ?? "when this month ends"}, nothing charged twice; 7-day full refund.
                      </p>
                      <button type="button" disabled={busy !== null} onClick={switchToYearly} className={`${btn} p-btn--primary justify-self-start`}>{busy === "switch" ? "Opening…" : "Switch to yearly"}</button>
                    </div>
                  )}
                  {offer === "pause" && (
                    <div className="grid min-w-0 gap-2">
                      <p style={{ font: "600 15px/1.3 var(--font-read)" }}>Pause instead</p>
                      <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>No charges while paused. Your watchlist and profile stay as they are.</p>
                      <div className="flex flex-wrap gap-1.5" role="group" aria-label="How long">
                        {MONTHS.map((m) => (
                          <button key={m} type="button" aria-pressed={months === m} onClick={() => setMonths(m)} className="p-chip">{monthsLabel(m)}</button>
                        ))}
                      </div>
                      {months && (
                        <>
                          <p className="p-mono uppercase" style={{ fontSize: 11, color: "var(--ink-3)" }}>Plus until {until ?? "this month ends"} · resumes {resumes}</p>
                          <button type="button" disabled={busy !== null} onClick={pause} className={`${btn} p-btn--primary justify-self-start`}>{busy === "pause" ? "Pausing…" : `Pause for ${monthsLabel(months)}`}</button>
                        </>
                      )}
                    </div>
                  )}
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-3" style={{ borderTop: "1px solid var(--line)" }}>
                    {footnote}
                    {cancelAnyway("ghost")}
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap items-center justify-between gap-2.5">{footnote}{cancelAnyway("secondary")}</div>
              )}
              {note && <p role="status" style={{ font: "500 13.5px/1.45 var(--font-read)", color: "var(--danger)" }}>{note}</p>}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
