"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Check } from "@/components/icons";
import { Sheet } from "@/components/story/Sheet";
import { Alert } from "@/components/ui";
import { track } from "@/lib/analytics";
import { fetchPlans, rupees, subscribe, type PlansOut } from "@/lib/billing";
import { useSession } from "@/lib/session";

// The moment a reader meets a limit (Design System v2 · money/UpgradeSheetBody):
// a sheet over the story, not a wall. The heading says why it opened, the count
// says what just happened, two lines say what Plus changes, then the price of
// the day and one action. A signed-in reader pays right here (Razorpay's sheet
// opens over this one); a stranger is sent to sign in with the way back.
// Escape, the scrim and the close button all work; the story stays underneath.
export type UpgradeReason = "ask-limit" | "ask-rest" | "generic";

const HEADING: Record<UpgradeReason, string> = {
  "ask-limit": "Ask more of this story",
  "ask-rest": "Ask is resting for free readers today",
  generic: "Ask more of every story",
};
// common/quota.PLUS_ASK_PER_DAY
const PLUS_ASK = 100;
const GAINS = [`${PLUS_ASK} questions a day, answered from the whole story`, "Ask stays on when the free tier rests"];

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
  const [plans, setPlans] = useState<PlansOut | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [declined, setDeclined] = useState<string | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
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
  const title = session ? HEADING[reason] : "Keep asking with an account";

  async function pay() {
    if (!session || !monthly) return;
    setBusy(true);
    setDeclined(null);
    setFailed(null);
    try {
      await subscribe(monthly.plan, session.token, session.email, (_kind, detail) => setDeclined(detail));
      setDone(true);
      onSubscribed?.();
    } catch (e) {
      const m = e instanceof Error ? e.message : "";
      if (m !== "dismissed") setFailed(m || "The payment did not go through. Nothing was charged.");
    } finally {
      setBusy(false);
    }
  }

  const cta = "p-btn p-btn--primary p-btn--lg p-btn--block";
  let action: React.ReactNode;
  if (plans === undefined) action = <button type="button" disabled className={cta}>Loading…</button>;
  else if (!ready) action = <p className="p-alert p-alert--info">Plus opens soon</p>;
  else if (session)
    action = <button type="button" disabled={busy} onClick={pay} className={cta}>{busy ? "Opening…" : `Get Plus · ${rupees(monthly!.amount_paise)} a month`}</button>;
  else action = <Link href={`/signin?next=${encodeURIComponent(next)}`} className={cta}>Sign in to get Plus</Link>;

  return (
    <Sheet variant="dialog" labelledBy="upgrade-title" onClose={onClose} closeRef={closeRef}>
      <div className="grid gap-3.5 overflow-y-auto px-5 pb-[calc(env(safe-area-inset-bottom)+20px)] pt-1 lg:px-6 lg:pb-6">
        {done ? (
          <>
            <div role="status" className="grid gap-2.5">
              <h2 id="upgrade-title" style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>You&rsquo;re on Plus.</h2>
              <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>Ask is back on — {PLUS_ASK} questions a day. Razorpay has emailed your receipt.</p>
            </div>
            <button type="button" onClick={onClose} className="p-btn p-btn--primary p-btn--block">Back to the story</button>
          </>
        ) : (
          <>
            <p className="p-count uppercase">
              <span>Prism Plus</span>
              {used != null && limit != null && <> · <span>{used} of {limit} today</span></>}
            </p>
            <h2 id="upgrade-title" className="text-balance" style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>{title}</h2>
            <ul className="grid gap-2">
              {GAINS.map((line) => (
                <li key={line} className="grid grid-cols-[18px_minmax(0,1fr)] gap-2" style={{ font: "var(--t-body-s)" }}>
                  <span className="mt-1" aria-hidden><Check size={14} /></span>
                  <span>{line}</span>
                </li>
              ))}
            </ul>
            {declined && (
              <Alert tone="error" title="The payment did not go through">
                {declined}. Nothing was charged; Razorpay&rsquo;s sheet is still open — try UPI or another card.
              </Alert>
            )}
            {failed && <Alert tone="error" title="The payment did not go through">{failed}</Alert>}
            {action}
            <Link href={next} className="inline-flex min-h-[44px] items-center justify-self-center text-[14px] font-semibold" style={{ color: "var(--accent)" }} onClick={onClose}>All plans →</Link>
            <p className="text-center text-[12.5px] leading-[1.45]" style={{ color: "var(--ink-3)" }}>
              {plans?.offer ? "Launch offer, held for 12 months. " : ""}GST included. Cancel any time; paid time is kept.
            </p>
          </>
        )}
      </div>
    </Sheet>
  );
}
