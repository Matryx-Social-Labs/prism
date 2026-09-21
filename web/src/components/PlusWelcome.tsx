"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Check } from "@/components/icons";
import { PLAN_LABEL } from "@/components/PlanCard";
import { track } from "@/lib/analytics";
import { fetchMySubscription, rupees, type MySubscription } from "@/lib/billing";
import { billingDay } from "@/lib/dateline";
import { safeNext } from "@/lib/next";
import { useSession } from "@/lib/session";

// Where a reader lands the moment they have paid: told plainly that Plus is
// on, what changed, when the next charge is, that the receipt is in their
// inbox — and one primary way back to what they were reading. No upsell, no
// tour; the door they came in by.
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

  return (
    <div className="mx-auto w-full max-w-[var(--reading)] px-5 pb-24 pt-12 sm:px-8 lg:pt-20">
      <p className="meta-line"><span>Prism Plus</span>{sub?.price_paise ? <><span className="dot" /><span>{label} · {rupees(sub.price_paise)}</span></> : null}</p>
      <h1 className="font-record mt-3 text-[36px] font-medium leading-[1.08] tracking-[-0.015em] text-balance sm:text-[44px]">You&rsquo;re on Plus.</h1>
      <p className="mt-4 text-[17px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>
        Thank you. Everything below is on from this moment, on every story.
      </p>
      <ul className="mt-6 flex flex-col">
        {[
          <><b className="font-semibold">100 questions a day</b> — the box no longer rests for you.</>,
          <><b className="font-semibold">The stronger model</b>, reading the <b className="font-semibold">whole story</b>, not one development.</>,
          <>Ask <b className="font-semibold">stays on</b> when the free box rests.</>,
        ].map((line, i) => (
          <li key={i} className="flex items-start gap-2.5 border-t py-3 text-[16px] leading-[1.55]" style={{ borderColor: "var(--line)" }}>
            <span className="mt-[4px] shrink-0" aria-hidden><Check size={16} /></span>
            <span>{line}</span>
          </li>
        ))}
      </ul>
      <dl className="mt-6 grid gap-x-8 gap-y-3 border-t pt-4 text-[14.5px] sm:grid-cols-2" style={{ borderColor: "var(--line)" }}>
        <div>
          <dt className="font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>Next charge</dt>
          <dd className="mt-1">{renews ?? "Shown on your account shortly"}</dd>
        </div>
        <div>
          <dt className="font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>Receipt</dt>
          <dd className="mt-1">Razorpay has emailed it{session ? ` to ${session.email}` : ""}.</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>Changing your mind</dt>
          <dd className="mt-1">Cancel in one click from your account, any time; you keep Plus to the end of the period you paid for.</dd>
        </div>
      </dl>
      <div className="mt-8 flex flex-wrap items-center gap-3">
        <Link href={next} className="btn btn-primary btn-lg">{next.startsWith("/story/") ? "Back to the story" : "Continue reading"}</Link>
        <Link href="/account" className="btn btn-ghost">Your account</Link>
      </div>
    </div>
  );
}
