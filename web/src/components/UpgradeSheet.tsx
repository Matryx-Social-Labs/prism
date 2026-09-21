"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Check, Close } from "@/components/icons";
import { track } from "@/lib/analytics";
import { fetchPlans, rupees, subscribe, type PlansOut } from "@/lib/billing";
import { useSession } from "@/lib/session";

// The moment a reader meets a limit (DESIGN.md § Plus): a sheet, not a wall.
// It says what just happened in counted words, what Plus changes in three
// lines, the price of the day, and one action. A signed-in reader pays right
// here (Razorpay's sheet opens over this one); a stranger is sent to sign in
// with the way back. Nothing is hidden behind it — Escape, the scrim and the
// close button all work, and the reader keeps whatever they were reading.
export type UpgradeReason = "ask-limit" | "ask-rest" | "generic";

export function UpgradeSheet({
  open,
  onClose,
  reason = "generic",
  used,
  limit,
  onSubscribed,
}: {
  open: boolean;
  onClose: () => void;
  reason?: UpgradeReason;
  used?: number;
  limit?: number;
  onSubscribed?: () => void;
}) {
  const session = useSession();
  const [plans, setPlans] = useState<PlansOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    track("Subscribe", { stage: "prompt", from: reason });
    fetchPlans().then(setPlans).catch(() => setPlans(null));
    closeRef.current?.focus({ preventScroll: true });
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!open) return null;
  const monthly = plans?.plans.find((p) => p.plan === "plus_monthly");
  const ready = !!plans?.checkout_ready && !!monthly;
  const next = typeof window === "undefined" ? "/plus" : `/plus?from=${reason}`;

  const title =
    reason === "ask-limit" && limit
      ? `You’ve asked today’s ${limit}.`
      : reason === "ask-rest"
        ? "Ask is resting for free readers today."
        : "Ask more of every story.";

  async function pay() {
    if (!session || !monthly) return;
    setBusy(true);
    setNote(null);
    try {
      await subscribe(monthly.plan, session.token, session.email, (_kind, detail) => setNote(`${detail}. The sheet is still open — try UPI or another card.`));
      setDone(true);
      onSubscribed?.();
    } catch (e) {
      const m = e instanceof Error ? e.message : "";
      if (m !== "dismissed") setNote(m || "Payment did not go through.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-[60]" style={{ background: "rgba(20,22,19,.35)" }} onClick={onClose} aria-hidden />
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="upgrade-title"
        className="upgrade-sheet fixed inset-x-0 bottom-0 z-[61] flex max-h-[86vh] flex-col overflow-y-auto rounded-t-[16px] border-t p-5 pb-[calc(env(safe-area-inset-bottom)+20px)] lg:inset-auto lg:left-1/2 lg:top-1/2 lg:w-[440px] lg:-translate-x-1/2 lg:-translate-y-1/2 lg:rounded-[16px] lg:border lg:p-6"
        style={{ background: "var(--bg-elevated)", borderColor: "var(--line-strong)", boxShadow: "var(--shadow-2)" }}
      >
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <p className="meta-line"><span>Prism Plus</span>{used != null && limit != null && <><span className="dot" /><span>{used} of {limit} today</span></>}</p>
            <h2 id="upgrade-title" className="font-record mt-2 text-[26px] font-bold leading-[1.15] tracking-[-0.01em] text-balance">{title}</h2>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} aria-label="Close" className="grid h-10 w-10 flex-none place-items-center rounded-full border" style={{ borderColor: "var(--line)", color: "var(--ink)" }}>
            <Close />
          </button>
        </div>

        {done ? (
          <p className="mt-5 text-[15px] leading-[1.6]" role="status">
            You&rsquo;re on Plus. Ask away — and manage it any time from <Link href="/you" className="font-semibold underline underline-offset-4">your account</Link>.
          </p>
        ) : (
          <>
            <ul className="mt-4 flex flex-col">
              {[
                <><b className="font-semibold">100 questions a day</b> instead of 10</>,
                <><b className="font-semibold">The stronger model</b>, reading the <b className="font-semibold">whole story</b></>,
                <>Ask <b className="font-semibold">stays on</b> when the free box rests</>,
              ].map((line, i) => (
                <li key={i} className="flex items-start gap-2.5 border-t py-2.5 text-[14.5px] leading-[1.5]" style={{ borderColor: "var(--line)" }}>
                  <span className="mt-[3px] shrink-0" aria-hidden><Check size={16} /></span>
                  <span>{line}</span>
                </li>
              ))}
            </ul>

            <div className="mt-5 flex flex-wrap items-center gap-3">
              {!plans ? (
                <span className="pulse-skel block h-12 w-44 rounded-full" style={{ background: "var(--sunken)" }} aria-hidden />
              ) : !ready ? (
                <span className="font-mono text-[11px] uppercase tracking-[0.03em]" style={{ color: "var(--ink-3)" }}>Plus opens soon</span>
              ) : session ? (
                <button type="button" disabled={busy} onClick={pay} className="btn btn-primary btn-lg">
                  {busy ? "Opening…" : `Get Plus · ${rupees(monthly!.amount_paise)} a month`}
                </button>
              ) : (
                <Link href={`/signin?next=${encodeURIComponent(next)}`} className="btn btn-primary btn-lg">Sign in to get Plus · {rupees(monthly!.amount_paise)} a month</Link>
              )}
              <Link href={next} className="btn btn-ghost" onClick={onClose}>All plans →</Link>
            </div>
            {note && <p className="mt-3 text-[13.5px]" role="status" style={{ color: "var(--danger)" }}>{note}</p>}
            <p className="mt-4 text-[12.5px] leading-[1.5]" style={{ color: "var(--ink-3)" }}>
              GST included · cancel any time from your account · Razorpay
            </p>
          </>
        )}
      </section>
    </>
  );
}
