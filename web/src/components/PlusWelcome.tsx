"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { PLAN_LABEL, refundOpen } from "@/components/PlanCard";
import { track } from "@/lib/analytics";
import { fetchMySubscription, rupees, type MySubscription } from "@/lib/billing";
import { billingDay } from "@/lib/dateline";
import { safeNext } from "@/lib/next";
import { useSession } from "@/lib/session";

// Where a reader lands the moment they have paid (Design System v2 · money
// board, Welcome): told plainly that Plus is on, what changed, when the next
// charge is, where the receipt is and how to change their mind — then the
// door they came in by. No upsell, no tour. Every fact is the subscription's own.
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
    ...(sub?.price_paise ? [["Plan", `${label} · ${rupees(sub.price_paise)} · GST included`] as [string, string]] : []),
    ["Next charge", renews ?? "Shown on your account shortly"],
    ["Receipt", <>Razorpay has emailed it{session ? ` to ${session.email}` : ""}; it is also under Payments in <Link href="/account" className="p-link">your account</Link>.</>],
    [
      "Changing your mind",
      refundUntil
        ? `Full refund until ${refundUntil}, in one click from your account.`
        : "Cancel in one click from your account, any time; you keep Plus to the end of the period you paid for.",
    ],
  ];
  const big = "p-btn p-btn--lg max-sm:w-full";

  return (
    <div className="mx-auto grid w-full max-w-[560px] gap-[18px] px-[var(--gutter)] pb-24 pt-8 lg:py-[72px]">
      {sub?.plan && sub.plan !== "free" && <p className="p-mono uppercase" style={{ fontSize: 11.5, color: "var(--ink-3)" }}>{sub.plan === "founding" ? "Founding member" : "Plus is on"}</p>}
      <h1 className="text-balance [font:var(--t-display-l)] lg:[font:var(--t-display-xl)]" style={{ letterSpacing: "var(--track-display)" }}>You&rsquo;re on Plus.</h1>
      <p className="max-w-[60ch]" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
        Ask is on at 100 questions a day, answered from the whole story, and it stays on when the free tier rests.
      </p>
      <dl className="m-0 grid gap-0.5 pt-3.5 sm:grid-cols-[180px_minmax(0,1fr)] sm:gap-x-4 sm:gap-y-3" style={{ borderTop: "1px solid var(--line)" }}>
        {facts.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="p-mono pt-2.5 uppercase sm:pt-0.5" style={{ fontSize: 11.5, color: "var(--ink-3)" }}>{k}</dt>
            <dd className="m-0" style={{ font: "var(--t-body-s)" }}>{v}</dd>
          </div>
        ))}
      </dl>
      <div className="flex flex-wrap gap-2.5">
        <Link href={next} className={`${big} p-btn--primary`}>{next.startsWith("/story/") ? "Back to the story" : "Continue reading"}</Link>
        <Link href="/account" className={`${big} p-btn--secondary`}>Your account</Link>
      </div>
      {next !== "/feed" && <Link href="/feed" className="p-link inline-flex min-h-[44px] items-center justify-self-start" style={{ font: "600 14.5px/1 var(--font-read)" }}>Continue reading today&rsquo;s record →</Link>}
    </div>
  );
}
