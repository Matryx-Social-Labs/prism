"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Check, ChevronDown, Dash } from "@/components/icons";
import { Reveal } from "@/components/Reveal";
import { SectionHead } from "@/components/SectionHead";
import { Alert } from "@/components/ui";
import { track } from "@/lib/analytics";
import { ASK_QUESTIONS as ASK, fetchPlans, gstIncluded, LENS_READS, rupees, subscribe, type PlanOut, type PlansOut } from "@/lib/billing";
import { billingDay } from "@/lib/dateline";
import { CHECKOUT_SOON_FAQ, FOUNDING_SEATS, PLUS_FAQ } from "@/lib/plusFaq";
import { safeNext } from "@/lib/next";
import { faqLd, jsonLd } from "@/lib/seo";
import { fetchMe, useSession } from "@/lib/session";

// The pricing page (Design System v2 · Plus): a provenance strip, the headline,
// a monthly/yearly switch, three plans side by side with the recommended one
// ruled in ink and accent, one trust line, then "Side by side" and "Before you
// pay" in two columns. Every number is the API's or the cap the server
// enforces; nothing here is a promise the product does not keep today. Plus
// sells the lenses and Ask, never a model (PRODUCT.md; founder decision #2,
// 27 Sep). A plan is charged automatically until the reader cancels, at the
// price they joined at (founder, 28 Sep; common/razorpay.TOTAL_COUNT); no line
// promises a lock or what a plan will cost later. While founding memberships
// are offered, founding is the recommended card (founder, 2026-09-29).

type Period = "month" | "year";

// Answered on the page and, word for word, in its FAQPage JSON-LD (lib/seo
// faqLd): the markup must equal the visible text.
/** Said first while checkout is shut (plans.checkout_ready false, e.g. on test keys). */


function Feature({ ok = true, children }: { ok?: boolean; children: React.ReactNode }) {
  return (
    <li className="grid grid-cols-[18px_minmax(0,1fr)] gap-2" style={{ font: "var(--t-body-s)", color: ok ? "var(--ink)" : "var(--ink-3)" }}>
      <span className="mt-[5px]" aria-hidden>{ok ? <Check size={14} /> : <Dash size={14} />}</span>
      <span>{children}</span>
    </li>
  );
}

/** A plan card (money/PricingCard): the recommended one is ruled in ink with the accent on top; otherwise the founding card's top rule is dashed. */
function PlanColumn({ kind, name, price, per, note, action, recommended: rec = false, soldOut = false, children }: {
  kind: "plus" | "free" | "founding";
  name: string;
  price?: React.ReactNode;
  per?: string;
  note?: string | null;
  action?: React.ReactNode;
  recommended?: boolean;
  soldOut?: boolean;
  children?: React.ReactNode;
}) {
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

/** A price on sale, its single total with the GST inside it (E-Com R7(1)(e)): "₹149 a month, including ₹22.73 GST (18%)." */
const priced = (p: PlanOut) => `${rupees(p.amount_paise)} a ${p.period}, ${gstIncluded(p.amount_paise)}.`;

/** `initialPlans` is the server's read (app/plus/page.tsx), so the HTML a crawler gets carries the prices; the client refreshes it. */
export function PlusPage({ initialPlans = null }: { initialPlans?: PlansOut | null }) {
  const session = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const from = params.get("from");
  // Where the buyer came from (a story, by the door they used): the welcome
  // page's way on, and sign-in's way back here (audit 2026-09-29, P1-3).
  const back = safeNext(params.get("next"));
  const [plans, setPlans] = useState<PlansOut | null>(initialPlans);
  const [plansFailed, setPlansFailed] = useState(false);
  const [myPlan, setMyPlan] = useState<string | null>(null);
  const askedPeriod = params.get("period");
  const [chosenPeriod, setPeriod] = useState<Period | null>(askedPeriod === "month" || askedPeriod === "year" ? askedPeriod : null);
  const [busy, setBusy] = useState<string | null>(null);
  const [declined, setDeclined] = useState<string | null>(null);
  const [failed, setFailed] = useState<{ plan: string; message: string } | null>(null);

  const loadPlans = () => {
    setPlansFailed(false);
    fetchPlans().then(setPlans).catch(() => setPlansFailed(true));
  };
  useEffect(loadPlans, []);
  useEffect(() => {
    track("Subscribe", { stage: "page", from: from ?? "direct" });
  }, [from]);
  useEffect(() => {
    setMyPlan(null);
    if (!session) return;
    fetchMe(session).then((m) => setMyPlan(m.plan ?? "free")).catch(() => setMyPlan("free"));
  }, [session]);

  const byPlan = useMemo(() => Object.fromEntries((plans?.plans ?? []).map((p) => [p.plan, p])) as Record<string, PlanOut | undefined>, [plans]);
  const monthly = byPlan.plus_monthly;
  const yearly = byPlan.plus_yearly;
  const founding = byPlan.founding;
  // While founding is offered it is the yearly recommendation, so the switch
  // opens on the month; a period in the link always wins.
  const period: Period = chosenPeriod ?? (founding ? "month" : "year");
  const plus = period === "year" ? yearly ?? monthly : monthly ?? yearly;
  // Arithmetic on the API's own figures, never a typed number.
  const yearlySaving = monthly && yearly ? monthly.amount_paise * 12 - yearly.amount_paise : null;
  const perMonth = yearly ? Math.round(yearly.amount_paise / 1200) * 100 : null;
  const foundingLess = founding && yearly ? yearly.amount_paise - founding.amount_paise : null;

  const onPlus = myPlan === "plus";
  const ready = !!plans?.checkout_ready;
  const offerEnds = plans?.offer_ends ? billingDay(plans.offer_ends, { long: true }) : null;
  const plusPlan = period === "year" ? "plus_yearly" : "plus_monthly";
  const plusCta = period === "year" ? "Get Plus yearly" : "Get Plus monthly";
  const foundingCta = founding ? `Become a founding member · ${rupees(founding.amount_paise)} a year` : "";
  const plusNote = plus
    ? [
        priced(plus),
        period === "year" && perMonth ? `≈ ${rupees(perMonth)} a month.` : null,
        "Renews until you cancel.",
        period === "year" && foundingLess && foundingLess > 0 ? `Founding membership is ${rupees(foundingLess)} a year less while seats last.` : null,
      ].filter(Boolean).join(" ")
    : null;
  // Remaining seats, said as remaining: "500 of 500 seats" read as sold out.
  const seats = plans && plans.founding_left >= FOUNDING_SEATS ? `Limited to ${FOUNDING_SEATS} members` : `${plans?.founding_left} of ${FOUNDING_SEATS} seats left`;
  const faq = plans && !plans.checkout_ready ? [CHECKOUT_SOON_FAQ, ...PLUS_FAQ] : PLUS_FAQ;
  // Sign-in returns here with the door, the way on and the period the reader chose.
  const signinBack = new URLSearchParams({ ...(from && { from }), ...(back && { next: back }), period }).toString();

  async function buy(plan: string) {
    if (!session) return;
    setBusy(plan);
    setDeclined(null);
    setFailed(null);
    try {
      await subscribe(plan, session.token, session.email, (_kind, detail) => setDeclined(detail));
      setMyPlan("plus");
      router.push(`/plus/welcome${back ? `?next=${encodeURIComponent(back)}` : ""}`);
    } catch (e) {
      const m = e instanceof Error ? e.message : "";
      if (m !== "dismissed") setFailed({ plan, message: m || "Nothing was charged." });
    } finally {
      setBusy(null);
    }
  }

  /** The one action a plan card carries, by who is looking. Busy words replace the label. */
  function Action({ plan, primary, label, cls: extra = "p-btn--block" }: { plan: string; primary: boolean; label: string; cls?: string }) {
    const cls = `p-btn ${extra} ${primary ? "p-btn--primary" : "p-btn--secondary"}`;
    if (onPlus) return <StateBox>Your plan</StateBox>;
    if (!plans || (session && myPlan === null)) return <button type="button" disabled className={cls}>Loading…</button>;
    if (!ready) return <StateBox dashed>Opens soon</StateBox>;
    if (!session) return <Link href={`/signin?next=${encodeURIComponent(`/plus?${signinBack}`)}`} className={cls}>Sign in to continue</Link>;
    return (
      <button type="button" disabled={busy !== null} onClick={() => buy(plan)} className={cls}>
        {busy === plan ? "Opening…" : label}
      </button>
    );
  }

  // The offer closes on a date or at a subscriber count, whichever comes first
  // (common/billing.offer_open), so the date is when it ends at the latest.
  const offerBadge = plans?.offer ? `Launch offer${offerEnds ? ` · ends by ${offerEnds}` : ""}` : null;
  // Founding memberships are sold only on the launch offer and only while seats remain
  // (common/billing.prices): gone because they are taken is said; gone because the offer closed is left out.
  const foundingGone = !founding && !!plans && plans.founding_left <= 0;

  const plusCard = (
    <PlanColumn
      kind="plus"
      name="Plus"
      recommended={!founding}
      price={plus ? rupees(plus.amount_paise) : <span className="p-skel inline-block h-9 w-28 align-middle" aria-hidden />}
      per={period === "year" ? "/ year" : "/ month"}
      note={plusNote}
      action={<Action plan={plusPlan} primary={!founding} label={plusCta} />}
    >
      <Feature><b className="font-semibold">Every lens on every story</b>, as often as you like</Feature>
      <Feature><b className="font-semibold">{ASK.plus} questions a day</b> on any story</Feature>
      <Feature>Answers from the <b className="font-semibold">whole story</b> — the reports of every related record</Feature>
      <Feature>Ask <b className="font-semibold">stays on</b> when the free box rests for the day</Feature>
      <Feature>Everything in Free</Feature>
    </PlanColumn>
  );
  const freeCard = (
    <PlanColumn
      kind="free"
      name="Free"
      price="₹0"
      per="forever"
      note="No card, no trial clock."
      action={session ? <StateBox>{onPlus ? "Included" : "Your plan"}</StateBox> : <Link href="/feed" className="p-btn p-btn--secondary p-btn--block">Keep reading free</Link>}
    >
      <Feature>Every record, source, verified quote, coverage count and clip, forever</Feature>
      {/* Without an account the count is per visit (a browser session), not per day. */}
      <Feature><b className="font-semibold">{LENS_READS.free} lens readings a day</b> with an account, {LENS_READS.anon} a visit without</Feature>
      <Feature><b className="font-semibold">{ASK.free} questions a day</b> with an account, {ASK.anon} a visit without</Feature>
      <Feature ok={false}>Answers from this record only</Feature>
      <Feature ok={false}>Ask rests for the day when the free box is spent</Feature>
    </PlanColumn>
  );
  const foundingCard = founding ? (
    <PlanColumn
      kind="founding"
      name="Founding member"
      recommended
      price={rupees(founding.amount_paise)}
      per="/ year"
      // Its renewal beside its price (docs/COMPLIANCE-INDIA.md N7(a)): the price joined at, until cancelled.
      note={`${priced(founding)} Renews at ${rupees(founding.amount_paise)} a year until you cancel. 7-day full refund.`}
      action={onPlus ? null : <Action plan="founding" primary label={foundingCta} />}
    >
      <Feature>Everything in Plus</Feature>
      {/* True by common/razorpay.TOTAL_COUNT (renews until cancelled) and the Terms' "keeps the price you joined at". */}
      <Feature>Your price is kept for as long as you stay subscribed, as Prism adds outlets and languages</Feature>
      <Feature><b className="font-semibold">{seats}</b></Feature>
    </PlanColumn>
  ) : foundingGone || !plans ? (
    <PlanColumn kind="founding" name="Founding member" soldOut note={plans ? "All seats are taken. Thank you." : null} />
  ) : null;
  // The recommended card leads (the wide first column, first on a phone).
  const cards = (
    founding
      ? [["founding", foundingCard], ["plus", plusCard], ["free", freeCard]]
      : [["plus", plusCard], ["free", freeCard], ["founding", foundingCard]]
  ).filter(([, card]) => card) as [string, React.ReactNode][];

  return (
    <div className="mx-auto w-full max-w-[1120px] px-[var(--gutter)] pb-24 pt-5 lg:pb-16 lg:pt-12">
      {/* ── Hero ─────────────────────────────────────────────────── */}
      <header className="max-w-[720px]">
        <div className="flex flex-wrap items-center gap-2">
          <p className="p-eyebrow">Prism Plus</p>
          {offerBadge && <span className="p-badge p-badge--accent">{offerBadge}</span>}
        </div>
        <h1 className="mt-2.5 text-balance [font:var(--t-display-l)] lg:[font:var(--t-display-xl)]" style={{ letterSpacing: "var(--track-display)" }}>Every lens on every story.</h1>
        <p className="mt-3 max-w-[60ch]" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
          The record stays free for everyone. Plus is for reading it for your work: every professional reading of every story, as often as you like, and a hundred questions a day, answered from the whole story.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-3.5">
          <div className="p-seg" role="tablist" aria-label="Billing period">
            <button type="button" role="tab" aria-selected={period === "month"} onClick={() => setPeriod("month")}>Monthly</button>
            <button type="button" role="tab" aria-selected={period === "year"} onClick={() => setPeriod("year")}>
              Yearly{yearlySaving && yearlySaving > 0 ? <span style={{ font: "500 11px/1 var(--font-mono)", color: "var(--accent)" }}>save {rupees(yearlySaving)}</span> : null}
            </button>
          </div>
          <span className="p-mono uppercase" style={{ fontSize: 11.5, color: "var(--ink-3)" }}>Prices include GST</span>
        </div>
      </header>

      {/* The server's figures stand if only the refresh failed. */}
      {plansFailed && !plans && (
        <div className="mt-6">
          <Alert tone="error" title="The plans could not be loaded" action={<button type="button" onClick={loadPlans} className="p-btn p-btn--sm p-btn--secondary max-sm:min-h-[44px]">Try again</button>}>
            Nothing on this page can be bought until they do.
          </Alert>
        </div>
      )}

      {/* ── Plans ─────────────────────────────────────────────────── */}
      <section aria-label="Plans" className={`mt-5 grid gap-3.5 ${cards.length === 3 ? "lg:grid-cols-[1.15fr_1fr_1fr]" : "lg:grid-cols-[1.15fr_1fr]"}`}>
        {cards.map(([key, card], i) => <Reveal key={key} className="min-w-0" delay={i * 40}>{card}</Reveal>)}
      </section>

      {/* Razorpay draws the checkout; Prism says what went wrong and what to do. */}
      {declined && (
        <div className="mt-4">
          <Alert tone="error" title="The payment did not go through">
            {declined}. Nothing was charged; Razorpay&rsquo;s sheet is still open — try UPI or another card.
          </Alert>
        </div>
      )}
      {failed && (
        <div className="mt-4">
          <Alert tone="error" title="The payment did not go through" action={<button type="button" onClick={() => buy(failed.plan)} className="p-btn p-btn--sm p-btn--secondary max-sm:min-h-[44px]">Try again</button>}>
            {failed.message}
          </Alert>
        </div>
      )}
      {onPlus && (
        <p className="mt-5 text-[15px]" role="status">
          You&rsquo;re on Plus. Manage it from <Link href="/account" className="p-link">your account</Link>.
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
                ["Lens readings", `${LENS_READS.free} a day · ${LENS_READS.anon} a visit without an account`, "Every lens, every story"],
                ["Questions a day", `${ASK.free} · ${ASK.anon} a visit without an account`, String(ASK.plus)],
                ["Answers drawn from", "This record", "The whole story"],
                // The shared free budget is counted per UTC day (common/quota.ask_burst_ok).
                ["When the free box rests", "Back at 5:30 am IST", "Stays on"],
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
          <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(faqLd(faq)) }} />
          {faq.map((f, i) => (
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
        <section className="mt-16 flex flex-wrap items-center gap-4 pt-5" style={{ borderTop: "var(--rule-section) solid var(--ink)" }}>
          <p className="min-w-0 flex-[1_1_280px]" style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>
            {founding
              ? `${rupees(founding.amount_paise)} a year as a founding member, while seats last.`
              : monthly && yearly ? `${rupees(yearly.amount_paise)} a year, or ${rupees(monthly.amount_paise)} a month.` : "Every lens on every story, and a hundred questions a day."}
          </p>
          {/* The page's one primary follows the recommended card. */}
          <div className="w-full sm:w-auto">
            {founding ? <Action plan="founding" primary label={foundingCta} cls="p-btn--lg max-sm:w-full" /> : <Action plan={plusPlan} primary label={plusCta} cls="p-btn--lg max-sm:w-full" />}
          </div>
        </section>
      )}
    </div>
  );
}
