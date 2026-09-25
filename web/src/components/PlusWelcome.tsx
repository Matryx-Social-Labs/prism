"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { PLAN_LABEL, refundOpen } from "@/components/PlanCard";
import { PrismMark } from "@/components/PrismMark";
import { track } from "@/lib/analytics";
import { fetchMySubscription, rupees, type MySubscription } from "@/lib/billing";
import { billingDay } from "@/lib/dateline";
import { safeNext } from "@/lib/next";
import { useSession } from "@/lib/session";

// Where a reader lands the moment they have paid: told plainly that Plus is
// on, what changed, when the next charge is, that the receipt is in their
// inbox — and one primary way back to what they were reading. No upsell, no
// tour; the door they came in by. Every fact is the subscription's own.
export function PlusWelcome() {
  const session = useSession();
  const params = useSearchParams();
  const next = safeNext(params.get("next")) ?? "/feed";
  const [sub, setSub] = useState<MySubscription | null>(null);
  useEffect(() => {
    track("Subscribe", { stage: "welcome" });
  }, []);
  useEffect(() => {
    if (!session) return;
    fetchMySubscription(session.token).then(setSub).catch(() => setSub(null));
  }, [session]);
  const label = PLAN_LABEL[sub?.plan ?? ""] ?? "Plus";
  const renews = sub?.current_period_end ? billingDay(sub.current_period_end, { long: true }) : null;
  const refundUntil = refundOpen(sub) ? billingDay(sub!.refundable_until!, { long: true }) : null;
  const facts: [string, React.ReactNode][] = [
    ...(sub?.price_paise ? [["Plan", `${label} · ${rupees(sub.price_paise)}`] as [string, string]] : []),
    ["Next charge", renews ?? "Shown on your account shortly"],
    ["Receipt", <>Razorpay has emailed it{session ? ` to ${session.email}` : ""}; it is also under Payments in <Link href="/account" className="p-link">your account</Link>.</>],
    [
      "Changing your mind",
      refundUntil
        ? `A full refund until ${refundUntil}, from your account. Or cancel in one click, any time; you keep Plus to the end of the period you paid for.`
        : "Cancel in one click from your account, any time; you keep Plus to the end of the period you paid for.",
    ],
  ];

  // Welcome (ui_kits/plus): the mark, the fact in one line, what changed, the
  // facts on mono labels, and the door back to what they were reading.
  return (
    <div className="mx-auto grid w-full max-w-[var(--reading)] gap-4 px-[var(--gutter)] pb-24 pt-12 lg:pt-[72px]">
      <PrismMark size={40} />
      <h1 className="text-balance" style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>You&rsquo;re on Plus.</h1>
      <p style={{ font: "var(--t-body-l)", color: "var(--ink-2)" }}>
        Thank you. From now on Ask answers 100 questions a day, drawn from the whole story on a larger model, and stays on when the free box rests.
      </p>
      <dl className="grid gap-x-4 gap-y-2.5 pt-3.5 sm:grid-cols-[160px_minmax(0,1fr)]" style={{ borderTop: "1px solid var(--line)", font: "var(--t-body-s)" }}>
        {facts.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="font-mono text-[11.5px] uppercase tracking-[0.04em] sm:pt-[3px]" style={{ color: "var(--ink-3)" }}>{k}</dt>
            <dd className="m-0 mb-1.5 sm:mb-0">{v}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-2 flex flex-wrap items-center gap-2.5">
        <Link href={next} className="p-btn p-btn--primary">{next.startsWith("/story/") ? "Back to the story" : "Continue reading"}</Link>
        <Link href="/account" className="p-btn p-btn--secondary">Your account</Link>
      </div>
    </div>
  );
}
