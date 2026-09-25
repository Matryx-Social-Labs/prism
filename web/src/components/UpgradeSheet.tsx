"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Check } from "@/components/icons";
import { Sheet } from "@/components/story/Sheet";
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
  const next = `/plus?from=${reason}`;

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
    <Sheet variant="dialog" labelledBy="upgrade-title" onClose={onClose} closeRef={closeRef}>
      <div className="grid gap-3.5 overflow-y-auto px-5 pb-[calc(env(safe-area-inset-bottom)+20px)] pt-1 lg:px-6 lg:pb-6">
        <p className="p-count uppercase">
          <span>Prism Plus</span>
          {used != null && limit != null && <> · <span>{used} of {limit} today</span></>}
        </p>
        {done ? (
          <>
            <div role="status" className="grid gap-2">
            <h2 id="upgrade-title" style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>You&rsquo;re on Plus.</h2>
            <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
              Ask is back on — 100 questions a day. Manage it any time from <Link href="/you" className="font-semibold" style={{ color: "var(--accent)" }}>your account</Link>.
            </p>
            </div>
            <button type="button" onClick={onClose} className="p-btn p-btn--primary p-btn--block">Back to the story</button>
          </>
        ) : (
          <>
            <h2 id="upgrade-title" className="text-balance" style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>{title}</h2>
            <ul className="grid gap-2">
              {[
                "100 questions a day instead of 10",
                "Answers from the whole story, on a larger model",
                "Ask stays on when the free box rests",
              ].map((line) => (
                <li key={line} className="grid grid-cols-[18px_1fr] gap-2" style={{ font: "var(--t-body-s)" }}>
                  <span className="mt-1" aria-hidden><Check size={14} /></span>
                  <span>{line}</span>
                </li>
              ))}
            </ul>
            {!plans ? (
              <span className="p-skel h-[52px] w-full" aria-hidden />
            ) : !ready ? (
              <p className="p-alert p-alert--info">Plus opens soon</p>
            ) : session ? (
              <button type="button" disabled={busy} onClick={pay} className="p-btn p-btn--primary p-btn--lg p-btn--block">
                {busy ? "Opening…" : `Get Plus · ${rupees(monthly!.amount_paise)} a month`}
              </button>
            ) : (
              <Link href={`/signin?next=${encodeURIComponent(next)}`} className="p-btn p-btn--primary p-btn--lg p-btn--block">Sign in to get Plus · {rupees(monthly!.amount_paise)} a month</Link>
            )}
            <Link href={next} className="justify-self-center py-2 text-[14px] font-semibold" style={{ color: "var(--accent)" }} onClick={onClose}>All plans →</Link>
            {note && <p className="p-alert p-alert--error" role="status">{note}</p>}
            <p className="text-center text-[12.5px] leading-[1.45]" style={{ color: "var(--ink-3)" }}>
              GST included · cancel any time from your account · Razorpay
            </p>
          </>
        )}
      </div>
    </Sheet>
  );
}
