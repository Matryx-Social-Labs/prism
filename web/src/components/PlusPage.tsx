"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Check, ChevronDown, Dash } from "@/components/icons";
import { Reveal } from "@/components/Reveal";
import { SectionHead } from "@/components/SectionHead";
import { track } from "@/lib/analytics";
import { fetchPlans, rupees, subscribe, type PlanOut, type PlansOut } from "@/lib/billing";
import { billingDay } from "@/lib/dateline";
import { fetchMe, useSession } from "@/lib/session";

// The pricing page (Design System v2 · Plus): a provenance strip, the headline,
// a monthly/yearly switch, three plans side by side with the recommended one
// ruled in ink and accent, one trust line, then "Side by side" and "Before you
// pay" in two columns. Every number is the API's or the cap the server
// enforces; nothing here is a promise the product does not keep today (plan
// renewal terms are an open founder decision — no price-after-launch claim).
const ASK = { anon: 3, free: 10, plus: 100 }; // common/quota.py
const FOUNDING_SEATS = 500; // common/billing.FOUNDING_CAP

type Period = "month" | "year";

const FAQ: { q: string; a: string }[] = [
  { q: "Can I cancel?", a: "Yes, in one click from your account, any time. You keep Plus until the end of the period you paid for and are not charged again." },
  { q: "What if I change my mind?", a: "A yearly or founding charge is refunded in full if you ask within 7 days — no questions. Monthly charges are not refunded; cancelling stops the next one." },
  { q: "Who charges me, and how?", a: "Razorpay processes the payment (UPI Autopay, cards, net banking). It is collected by Matryx Social Labs Private Limited on behalf of Prism Media Intelligence LLP until the LLP's own merchant account is live, so that is the name you may see on your statement." },
  { q: "Are the prices final?", a: "Yes. Every price on this page includes GST, and each charge comes with an invoice by email." },
  { q: "What does Plus not change?", a: "Reading. Every record, source, quote, coverage split and clip stays free for everyone, with or without an account. Plus changes how much you can ask of it." },
];

function Feature({ ok = true, children }: { ok?: boolean; children: React.ReactNode }) {
  return (
    <li className="grid grid-cols-[18px_minmax(0,1fr)] gap-2" style={{ font: "var(--t-body-s)", color: ok ? "var(--ink)" : "var(--ink-3)" }}>
      <span className="mt-[5px]" aria-hidden>{ok ? <Check size={14} /> : <Dash size={14} />}</span>
      <span>{children}</span>
    </li>
  );
}

/** A plan card (money/PricingCard): Plus is ruled in ink with the accent on top; the founding card's top rule is dashed. */
function PlanColumn({ kind, name, price, per, sub, note, action, soldOut = false, children }: {
  kind: "plus" | "free" | "founding";
  name: string;
  price?: React.ReactNode;
  per?: string;
  sub?: string | null;
  note?: string | null;
  action?: React.ReactNode;
  soldOut?: boolean;
  children?: React.ReactNode;
}) {
  const rec = kind === "plus";
  return (
    <article
      aria-label={name}
      className="flex h-full min-w-0 flex-col gap-3.5 p-[22px]"
      style={{
        background: "var(--surface)",
        borderRadius: "var(--r-lg)",
        border: rec ? "1.5px solid var(--ink)" : "1px solid var(--line)",
        borderTop: rec ? "4px solid var(--accent)" : kind === "founding" ? "1px dashed var(--line-strong)" : "1px solid var(--line)",
        opacity: soldOut ? 0.75 : 1,
      }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <h2 style={{ font: "var(--t-title)" }}>{name}</h2>
        {rec && <span className="p-badge p-badge--accent">Recommended</span>}
      </div>
      {price != null && (
        <p className="flex items-baseline gap-1.5">
          <span style={{ font: "600 40px/1 var(--font-record)", letterSpacing: "-0.02em" }}>{price}</span>
          {per && <span style={{ font: "500 14px/1 var(--font-read)", color: "var(--ink-3)" }}>{per}</span>}
        </p>
      )}
      {sub && <p className="p-count whitespace-normal" style={{ fontSize: 12, color: "var(--ink-2)" }}>{sub}</p>}
      {note && <p style={{ font: "400 13.5px/1.45 var(--font-read)", color: "var(--ink-2)" }}>{note}</p>}
      {children && <ul className="grid gap-2">{children}</ul>}
      {action && <div className="mt-auto pt-1">{action}</div>}
    </article>
  );
}

/** Where a card's action would be, when there is no action to take: a line box, not a dead button. */
function StateBox({ children, dashed = false }: { children: React.ReactNode; dashed?: boolean }) {
  return (
    <p className="flex min-h-[44px] items-center justify-center px-3 text-center" style={{ border: `1px ${dashed ? "dashed" : "solid"} var(--line-strong)`, borderRadius: "var(--r-control)", font: "600 14px/1.2 var(--font-read)", color: "var(--ink-3)" }}>
      {children}
    </p>
  );
}

export function PlusPage() {
  const session = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const from = params.get("from");
  const [plans, setPlans] = useState<PlansOut | null>(null);
  const [plansFailed, setPlansFailed] = useState(false);
  const [myPlan, setMyPlan] = useState<string | null>(null);
  const [period, setPeriod] = useState<Period>("year");
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const loadPlans = () => {
    setPlansFailed(false);
    fetchPlans().then(setPlans).catch(() => setPlansFailed(true));
  };
  useEffect(loadPlans, []);
  useEffect(() => {
    track("Subscribe", { stage: "page", from: from ?? "direct" });
  }, [from]);
  useEffect(() => {
    if (!session) return setMyPlan(null);
    fetchMe(session).then((m) => setMyPlan(m.plan ?? "free")).catch(() => setMyPlan("free"));
  }, [session]);

  const byPlan = useMemo(() => Object.fromEntries((plans?.plans ?? []).map((p) => [p.plan, p])) as Record<string, PlanOut | undefined>, [plans]);
  const monthly = byPlan.plus_monthly;
  const yearly = byPlan.plus_yearly;
  const founding = byPlan.founding;
  const plus = period === "year" ? yearly ?? monthly : monthly ?? yearly;
  // Arithmetic on the API's own figures, never a typed number.
  const yearlySaving = monthly && yearly ? monthly.amount_paise * 12 - yearly.amount_paise : null;
  const perMonth = yearly ? Math.round(yearly.amount_paise / 12) : null;

  const onPlus = myPlan === "plus";
  const ready = !!plans?.checkout_ready;
  const offerEnds = plans?.offer_ends ? billingDay(plans.offer_ends, { long: true }) : null;
  const plusPlan = period === "year" ? "plus_yearly" : "plus_monthly";

  async function buy(plan: string) {
    if (!session) return;
    setBusy(plan);
    setNote(null);
    try {
      await subscribe(plan, session.token, session.email, (_kind, detail) => setNote(`${detail}. The sheet is still open — try UPI or another card.`));
      setMyPlan("plus");
      router.push(`/plus/welcome${from ? `?next=${encodeURIComponent(from.startsWith("/") ? from : "/feed")}` : ""}`);
    } catch (e) {
      const m = e instanceof Error ? e.message : "";
      if (m !== "dismissed") setNote(m || "Payment did not go through.");
    } finally {
      setBusy(null);
    }
  }

  /** The one action a plan card carries, by who is looking. */
  function Action({ plan, primary, label }: { plan: string; primary: boolean; label: string }) {
    const cls = `p-btn p-btn--block ${primary ? "p-btn--primary" : "p-btn--secondary"}`;
    if (onPlus) return <StateBox>Your plan</StateBox>;
    if (!plans) return <span className="p-skel h-11 w-full" aria-hidden />;
    if (!ready) return <StateBox dashed>Opens soon</StateBox>;
    if (!session) return <Link href="/signin?next=/plus" className={cls}>Sign in to continue</Link>;
    return (
      <button type="button" disabled={busy !== null} onClick={() => buy(plan)} className={cls}>
        {busy === plan ? "Opening…" : label}
      </button>
    );
  }

  const strip = ["Prism Plus", ...(plans?.offer ? ["Launch offer", offerEnds ? `until ${offerEnds}` : "first 1,000 readers"] : [])].join(" · ");

  return (
    <div className="mx-auto w-full max-w-[1080px] px-[var(--gutter)] pb-24 pt-10 lg:pt-12">
      {/* ── Hero ─────────────────────────────────────────────────── */}
      <header>
        <p className="p-count whitespace-normal uppercase">{strip}</p>
        <h1 className="mt-2.5 text-balance lg:!text-[56px]" style={{ font: "var(--t-display-xl)", letterSpacing: "var(--track-display)" }}>Ask more of every story.</h1>
        <p className="mt-3 max-w-[56ch]" style={{ font: "var(--t-body-l)", color: "var(--ink-2)" }}>
          The evidence stays free for everyone. Plus is for the reader who asks more of it: answers drawn from the whole story, a hundred questions a day.
        </p>
        <div className="mt-6 p-seg" role="tablist" aria-label="Billing period">
          <button type="button" role="tab" aria-selected={period === "month"} onClick={() => setPeriod("month")}>Monthly</button>
          <button type="button" role="tab" aria-selected={period === "year"} onClick={() => setPeriod("year")}>
            Yearly{yearlySaving && yearlySaving > 0 ? <span style={{ font: "500 11px/1 var(--font-mono)", color: "var(--accent)" }}>save {rupees(yearlySaving)}</span> : null}
          </button>
        </div>
      </header>

      {plansFailed && (
        <p className="p-alert p-alert--error mt-6">
          <span>The plans could not be loaded. <button type="button" onClick={loadPlans} className="font-semibold underline underline-offset-4">Retry</button></span>
        </p>
      )}

      {/* ── Plans ─────────────────────────────────────────────────── */}
      <section aria-label="Plans" className="mt-5 grid gap-3.5 lg:grid-cols-[1.15fr_1fr_1fr]">
        <Reveal className="min-w-0">
          <PlanColumn
            kind="plus"
            name="Plus"
            price={plus ? rupees(plus.amount_paise) : <span className="p-skel inline-block h-9 w-28 align-middle" aria-hidden />}
            per={period === "year" ? "/ year" : "/ month"}
            note={plus ? [period === "year" && perMonth ? `≈ ${rupees(perMonth)} a month, GST included.` : "GST included; cancel any time.", plans?.offer ? "The price you join at is yours for 12 months." : ""].join(" ").trim() : null}
            action={<Action plan={plusPlan} primary label="Get Plus" />}
          >
            <Feature>Answers from the <b className="font-semibold">whole story</b> — every development&rsquo;s reports</Feature>
            <Feature><b className="font-semibold">{ASK.plus} questions a day</b> on any story</Feature>
            <Feature>Ask <b className="font-semibold">stays on</b> when the free box rests for the day</Feature>
            <Feature>A larger model on every answer</Feature>
            <Feature>Everything in Free</Feature>
          </PlanColumn>
        </Reveal>

        <Reveal className="min-w-0" delay={40}>
          <PlanColumn
            kind="free"
            name="Free"
            price="₹0"
            per="forever"
            note="No card, no trial clock."
            action={session ? <StateBox>{onPlus ? "Included" : "Your plan"}</StateBox> : <Link href="/signin?next=/feed" className="p-btn p-btn--secondary p-btn--block">Sign in free</Link>}
          >
            <Feature>Every record, source, verified quote, coverage count and clip, forever</Feature>
            <Feature><b className="font-semibold">{ASK.free} questions a day</b> with an account, {ASK.anon} without</Feature>
            <Feature>The standard model</Feature>
            <Feature ok={false}>Answers from this development only</Feature>
            <Feature ok={false}>Ask rests for the day when the free box is spent</Feature>
          </PlanColumn>
        </Reveal>

        <Reveal className="min-w-0" delay={80}>
          {founding ? (
            <PlanColumn
              kind="founding"
              name="Founding member"
              price={rupees(founding.amount_paise)}
              per="/ year"
              sub={`${plans!.founding_left} of ${FOUNDING_SEATS} seats · price locked 3 years`}
              action={<Action plan="founding" primary={false} label="Become a founding member" />}
            >
              <Feature>Everything in Plus</Feature>
              <Feature>{rupees(founding.amount_paise)} a year, <b className="font-semibold">held for three years</b></Feature>
              <Feature>One of the first {FOUNDING_SEATS} readers who paid for an independent record</Feature>
            </PlanColumn>
          ) : (
            <PlanColumn kind="founding" name="Founding member" soldOut note={plans ? "All seats are taken. Thank you." : null} />
          )}
        </Reveal>
      </section>

      {note && <p className="mt-4 text-[14px]" role="status" style={{ color: "var(--danger)" }}>{note}</p>}
      {onPlus && (
        <p className="mt-5 text-[15px]" role="status">
          You&rsquo;re on Plus. Manage it from <Link href="/you" className="p-link">your account</Link>.
        </p>
      )}

      <p className="mt-3 flex flex-wrap items-center gap-x-2.5 gap-y-1" style={{ font: "400 13px/1.45 var(--font-read)", color: "var(--ink-3)" }}>
        {["Payments by Razorpay", "UPI Autopay, cards, net banking", "GST included", "cancel any time"].map((t, i) => (
          <span key={t} className="contents">{i > 0 && <span className="p-meta__sep" aria-hidden />}<span>{t}</span></span>
        ))}
        <span className="p-meta__sep" aria-hidden /><Link href="/refunds" className="p-link">Refund policy</Link>
        <span className="p-meta__sep" aria-hidden /><Link href="/terms" className="p-link">Terms</Link>
      </p>

      {/* ── Side by side · Before you pay ─────────────────────────── */}
      <div className="mt-14 grid gap-12 lg:grid-cols-2">
        <section aria-labelledby="compare-title" className="min-w-0">
          <SectionHead id="compare-title" title="Side by side" />
          <table className="p-table">
            <thead>
              <tr>
                <th scope="col">What</th>
                <th scope="col" className="w-[28%]" style={{ textAlign: "center" }}>Free</th>
                <th scope="col" className="w-[28%]" style={{ textAlign: "center", color: "var(--ink)" }}>Plus</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Reading the record", "Everything", "Everything"],
                ["Questions a day", `${ASK.free} · ${ASK.anon} without an account`, String(ASK.plus)],
                ["The model", "Standard", "Stronger"],
                ["Answers drawn from", "This development", "The whole story"],
                ["When the free box rests", "Back at midnight UTC", "Stays on"],
                ["Price", "₹0", plus ? `${rupees(plus.amount_paise)} ${period === "year" ? "a year" : "a month"}` : "—"],
              ].map(([what, free, pl]) => (
                <tr key={what}>
                  <th scope="row" style={{ font: "500 14px/1.4 var(--font-read)", color: "var(--ink)", textTransform: "none", letterSpacing: "normal", borderBottomColor: "var(--line)" }}>{what}</th>
                  <td className="text-center" style={{ font: "500 13.5px/1.35 var(--font-read)", color: "var(--ink-2)" }}>{free}</td>
                  <td className="text-center" style={{ font: "600 13.5px/1.35 var(--font-read)" }}>{pl}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section aria-labelledby="faq-title" className="min-w-0">
          <SectionHead id="faq-title" title="Before you pay" />
          {FAQ.map((f, i) => (
            <details key={f.q} open={i === 0} className="group py-1" style={{ borderTop: "1px solid var(--line)" }}>
              <summary className="flex min-h-[52px] cursor-pointer list-none items-center gap-3 [&::-webkit-details-marker]:hidden" style={{ font: "600 15.5px/1.35 var(--font-read)" }}>
                <span className="min-w-0 flex-1">{f.q}</span>
                <span className="transition-transform group-open:rotate-180" style={{ color: "var(--ink-3)" }} aria-hidden><ChevronDown size={14} /></span>
              </summary>
              <p className="max-w-[62ch] pb-3.5" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{f.a}</p>
            </details>
          ))}
        </section>
      </div>

      {/* ── One more time ─────────────────────────────────────────── */}
      {!onPlus && (
        <section className="mt-16 flex flex-col items-start gap-4 pt-5" style={{ borderTop: "var(--rule-section) solid var(--ink)" }}>
          <p style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>A hundred questions a day, from the whole story.</p>
          <div className="w-full sm:w-auto sm:min-w-[280px]"><Action plan={plusPlan} primary label={plus ? `Get Plus · ${rupees(plus.amount_paise)} ${period === "year" ? "a year" : "a month"}` : "Get Plus"} /></div>
        </section>
      )}
    </div>
  );
}
