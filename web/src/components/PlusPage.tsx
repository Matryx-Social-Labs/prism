"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchMe, useSession } from "@/lib/session";
import { fetchPlans, rupees, subscribe, type PlansOut } from "@/lib/billing";

// The pricing page: what Plus gives, the plans as rows on hairlines, one
// primary action. Everything counted is read from the API (the offer, the
// founding seats left) or from the same constants the server enforces; nothing
// here is a promise the product does not keep today. Until the payment keys
// exist the rows say so instead of showing a button that cannot work.
const ASK = { anon: 3, free: 10, plus: 100 }; // common/quota.py — the caps the server enforces

export function PlusPage() {
  const session = useSession();
  const [plans, setPlans] = useState<PlansOut | null>(null);
  const [myPlan, setMyPlan] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const [plansFailed, setPlansFailed] = useState(false);
  const loadPlans = () => {
    setPlansFailed(false);
    fetchPlans().then(setPlans).catch(() => setPlansFailed(true));
  };
  useEffect(loadPlans, []);
  useEffect(() => {
    if (!session) return setMyPlan(null);
    fetchMe(session).then((m) => setMyPlan(m.plan ?? "free")).catch(() => setMyPlan("free"));
  }, [session]);

  async function buy(plan: string) {
    if (!session) return;
    setBusy(plan);
    setNote(null);
    try {
      await subscribe(plan, session.token, session.email);
      setMyPlan("plus");
      setNote("You're on Plus. Thank you.");
    } catch (e) {
      const m = e instanceof Error ? e.message : "";
      if (m !== "dismissed") setNote(m || "Payment did not go through.");
    } finally {
      setBusy(null);
    }
  }

  const onPlus = myPlan === "plus";
  const offerEnds = plans?.offer_ends ? new Date(plans.offer_ends).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }) : null;

  return (
    <div className="mx-auto w-full max-w-[var(--reading)] px-5 pb-20 pt-10 sm:px-8 lg:pt-14">
      <h1 className="font-record text-[34px] font-medium leading-[1.1] tracking-[-0.015em] text-balance sm:text-[40px]">Plus</h1>
      <p className="mt-3 text-[17px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>
        The record stays free for everyone. Plus is for the reader who asks more of it.
      </p>

      <ul className="mt-6 flex flex-col divide-y text-[16px] leading-[1.6]" style={{ borderColor: "var(--line)" }}>
        <li className="py-3" style={{ borderColor: "var(--line)" }}>
          <b className="font-semibold">{ASK.plus} questions a day</b> on any story — {ASK.free} with a free account, {ASK.anon} without one.
        </li>
        <li className="py-3" style={{ borderColor: "var(--line)" }}>
          <b className="font-semibold">The stronger model</b>, and answers drawn from the <b className="font-semibold">whole story</b> — every development's reports, not the one you are reading.
        </li>
        <li className="py-3" style={{ borderColor: "var(--line)" }}>
          <b className="font-semibold">Ask stays on</b> for you when the free question box rests for the day.
        </li>
      </ul>

      {plans?.offer && (
        <p className="mt-8 font-mono text-[12px] tracking-[0.02em]" style={{ color: "var(--ink-3)" }}>
          Launch offer{offerEnds ? ` · until ${offerEnds}` : ` · for the first 1,000 Plus readers`} · the price you join at is yours for 12 months
        </p>
      )}

      <section className="mt-3 border-t" style={{ borderColor: "var(--line)" }} aria-label="Plans">
        {!plans && !plansFailed && <p className="py-6 text-[14.5px]" style={{ color: "var(--ink-3)" }}>Loading plans…</p>}
        {plansFailed && (
          <p className="py-6 text-[14.5px]" style={{ color: "var(--danger)" }}>
            The plans could not be loaded. <button type="button" onClick={loadPlans} className="font-semibold underline underline-offset-4">Retry</button>
          </p>
        )}
        {plans?.plans.map((p, i) => {
          const primary = i === 0;
          const per = p.period === "month" ? "a month" : "a year";
          return (
            <div key={p.plan} className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b py-4" style={{ borderColor: "var(--line)" }}>
              <div className="min-w-0 flex-1">
                <p className="text-[16px] font-semibold">{p.label}</p>
                {p.plan === "founding" && (
                  <p className="text-[13.5px]" style={{ color: "var(--ink-3)" }}>{plans.founding_left} of 500 seats left</p>
                )}
              </div>
              <p className="font-mono text-[15px] tabular-nums">{rupees(p.amount_paise)} <span className="text-[12px]" style={{ color: "var(--ink-3)" }}>{per}</span></p>
              {onPlus ? null : !plans.checkout_ready ? (
                <span className="font-mono text-[11px] uppercase tracking-[0.03em]" style={{ color: "var(--ink-3)" }}>Opens soon</span>
              ) : !session ? (
                <Link href="/signin?next=/plus" className={`btn ${primary ? "btn-primary" : "btn-secondary"}`}>Sign in to subscribe</Link>
              ) : (
                <button type="button" disabled={busy !== null} onClick={() => buy(p.plan)} className={`btn ${primary ? "btn-primary" : "btn-secondary"}`}>
                  {busy === p.plan ? "Opening…" : p.plan === "founding" ? "Become a founding member" : "Subscribe"}
                </button>
              )}
            </div>
          );
        })}
      </section>

      {onPlus && (
        <p className="mt-5 text-[15px]" role="status">
          You&rsquo;re on Plus. Manage it from <Link href="/you" className="font-semibold underline underline-offset-4">your account</Link>.
        </p>
      )}
      {note && !onPlus && <p className="mt-4 text-[14px]" role="status" style={{ color: "var(--danger)" }}>{note}</p>}

      <p className="mt-8 text-[13.5px] leading-[1.6]" style={{ color: "var(--ink-3)" }}>
        Prices include GST. Cancel any time from your account; access continues to the end of the period you paid for.{" "}
        <Link href="/refunds" className="underline underline-offset-[3px]">Refund policy</Link>. Payments are collected by Matryx Social Labs Private Limited on behalf of Prism Media Intelligence LLP.
      </p>
    </div>
  );
}
