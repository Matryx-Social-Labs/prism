"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Check, Dash } from "@/components/icons";
import { Reveal } from "@/components/Reveal";
import { track } from "@/lib/analytics";
import { fetchPlans, rupees, subscribe, type PlanOut, type PlansOut } from "@/lib/billing";
import { fetchMe, useSession } from "@/lib/session";

// The pricing page (DESIGN.md § Plus). The shape every subscription page a
// reader already knows: a headline, a monthly/yearly control, three plans side
// by side with the recommended one marked, a side-by-side table, the questions
// people ask before paying, one footnote on who charges what. Built from the
// product's own parts — the `.seg` control, `.card`, hairline rows, the mono
// meta line — in the product's own ink; the one accent is the one action.
// Every number is the API's or the cap the server enforces; nothing here is a
// promise the product does not keep today.
const ASK = { anon: 3, free: 10, plus: 100 }; // common/quota.py
const FOUNDING_SEATS = 500; // common/billing.FOUNDING_CAP

type Period = "month" | "year";

const FAQ: { q: string; a: string }[] = [
  { q: "Can I cancel?", a: "Yes, in one click from your account, any time. You keep Plus until the end of the period you paid for and are not charged again." },
  { q: "What if I change my mind?", a: "A yearly or founding charge is refunded in full if you ask within 7 days — no questions. Monthly charges are not refunded; cancelling stops the next one." },
  { q: "Who charges me, and how?", a: "Razorpay processes the payment (UPI Autopay, cards, net banking). It is collected by Matryx Social Labs Private Limited on behalf of Prism Media Intelligence LLP until the LLP's own merchant account is live, so that is the name you may see on your statement." },
  { q: "Are the prices final?", a: "Yes. Every price on this page includes GST, and each charge comes with an invoice by email." },
  { q: "What happens when the offer's twelve months end?", a: "Your subscription completes and nothing renews on its own. We write to you first with the price of the day, and you decide." },
  { q: "What does Plus not change?", a: "Reading. Every record, source, quote, coverage split and clip stays free for everyone, with or without an account. Plus changes how much you can ask of it." },
];

function Row({ ok, children, muted = false }: { ok: boolean; children: React.ReactNode; muted?: boolean }) {
  return (
    <li className="flex items-start gap-2.5 border-t py-2.5 text-[14.5px] leading-[1.5]" style={{ borderColor: "var(--line)", color: muted ? "var(--ink-3)" : "var(--ink)" }}>
      <span className="mt-[3px] shrink-0" style={{ color: ok ? "var(--ink)" : "var(--ink-3)" }} aria-hidden>
        {ok ? <Check size={16} /> : <Dash size={16} />}
      </span>
      <span>{children}</span>
    </li>
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
  const offerEnds = plans?.offer_ends ? new Date(plans.offer_ends).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }) : null;

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
    if (onPlus) return <span className="font-mono text-[11px] uppercase tracking-[0.03em]" style={{ color: "var(--ink-3)" }}>{plan.startsWith("plus") || plan === "founding" ? "Your plan" : ""}</span>;
    if (!plans) return <span className="pulse-skel block h-10 w-32 rounded-full" style={{ background: "var(--sunken)" }} aria-hidden />;
    if (!ready) return <span className="font-mono text-[11px] uppercase tracking-[0.03em]" style={{ color: "var(--ink-3)" }}>Opens soon</span>;
    if (!session) return <Link href="/signin?next=/plus" className={`btn ${primary ? "btn-primary" : "btn-secondary"}`}>Sign in to continue</Link>;
    return (
      <button type="button" disabled={busy !== null} onClick={() => buy(plan)} className={`btn ${primary ? "btn-primary" : "btn-secondary"}`}>
        {busy === plan ? "Opening…" : label}
      </button>
    );
  }

  return (
    <div className="mx-auto w-full max-w-[1080px] px-5 pb-24 pt-10 sm:px-8 lg:pt-16">
      {/* ── Hero ─────────────────────────────────────────────────── */}
      <header className="mx-auto max-w-[640px] text-center">
        <p className="meta-line justify-center">
          <span>Prism Plus</span>
          {plans?.offer && (
            <>
              <span className="dot" />
              <span>Launch offer{offerEnds ? ` · until ${offerEnds}` : ` · first 1,000 readers`}</span>
            </>
          )}
        </p>
        <h1 className="font-record mt-3 text-[36px] font-medium leading-[1.08] tracking-[-0.015em] text-balance sm:text-[44px]">Ask more of every story.</h1>
        <p className="mt-4 text-[17px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>
          The record stays free for everyone. Plus is for the reader who needs answers from the whole story — a hundred times a day, on the stronger model.
        </p>
        <div className="mt-7 inline-flex flex-col items-center gap-2">
          <div className="seg" role="tablist" aria-label="Billing period">
            <button type="button" role="tab" aria-selected={period === "month"} onClick={() => setPeriod("month")}>Monthly</button>
            <button type="button" role="tab" aria-selected={period === "year"} onClick={() => setPeriod("year")}>
              Yearly{yearlySaving && yearlySaving > 0 ? <span className="font-mono text-[11px] font-normal" style={{ color: "var(--ink-3)" }}>save {rupees(yearlySaving)}</span> : null}
            </button>
          </div>
          {plans?.offer && <p className="font-mono text-[11px] tracking-[0.02em]" style={{ color: "var(--ink-3)" }}>The price you join at is yours for 12 months</p>}
        </div>
      </header>

      {plansFailed && (
        <p className="mx-auto mt-10 max-w-[640px] text-center text-[14.5px]" style={{ color: "var(--danger)" }}>
          The plans could not be loaded. <button type="button" onClick={loadPlans} className="font-semibold underline underline-offset-4">Retry</button>
        </p>
      )}

      {/* ── Plans ─────────────────────────────────────────────────── */}
      <section aria-label="Plans" className="mt-10 grid gap-4 lg:mt-12 lg:grid-cols-3 lg:items-start">
        {/* Plus first on the phone, centre on a desk. */}
        <Reveal className="order-1 lg:order-2">
          <article className="card relative flex flex-col p-6" style={{ borderColor: "var(--ink)", boxShadow: "var(--shadow-2)" }} aria-label="Plus">
            <span className="absolute -top-2.5 left-6 rounded-full px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-[0.03em]" style={{ background: "var(--ink)", color: "var(--bg)" }}>Recommended</span>
            <h2 className="text-[15px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-2)" }}>Plus</h2>
            <p className="mt-3 flex items-baseline gap-1.5">
              <span className="font-record text-[40px] font-medium leading-none tracking-[-0.02em]">{plus ? rupees(plus.amount_paise) : <span className="pulse-skel inline-block h-9 w-24 rounded" style={{ background: "var(--sunken)" }} />}</span>
              <span className="font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>{period === "year" ? "/ year" : "/ month"}</span>
            </p>
            <p className="mt-1 h-5 font-mono text-[11px] tracking-[0.02em]" style={{ color: "var(--ink-3)" }}>
              {period === "year" && perMonth ? `≈ ${rupees(perMonth)} a month · GST included` : plus ? "GST included · cancel any time" : ""}
            </p>
            <div className="mt-5"><Action plan={period === "year" ? "plus_yearly" : "plus_monthly"} primary label="Get Plus" /></div>
            <ul className="mt-5 flex flex-col">
              <Row ok><b className="font-semibold">{ASK.plus} questions a day</b> on any story</Row>
              <Row ok><b className="font-semibold">The stronger model</b> on every answer</Row>
              <Row ok>Answers from the <b className="font-semibold">whole story</b> — every development&rsquo;s reports</Row>
              <Row ok>Ask <b className="font-semibold">stays on</b> when the free box rests for the day</Row>
              <Row ok>Everything in Free</Row>
            </ul>
          </article>
        </Reveal>

        <Reveal className="order-2 lg:order-1" delay={40}>
          <article className="card flex flex-col p-6" aria-label="Free">
            <h2 className="text-[15px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-2)" }}>Free</h2>
            <p className="mt-3 flex items-baseline gap-1.5">
              <span className="font-record text-[40px] font-medium leading-none tracking-[-0.02em]">₹0</span>
              <span className="font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>forever</span>
            </p>
            <p className="mt-1 h-5 font-mono text-[11px] tracking-[0.02em]" style={{ color: "var(--ink-3)" }}>No card, no trial clock</p>
            <div className="mt-5">
              {session ? (
                <span className="font-mono text-[11px] uppercase tracking-[0.03em]" style={{ color: "var(--ink-3)" }}>{onPlus ? "Included" : "Your plan"}</span>
              ) : (
                <Link href="/signin?next=/feed" className="btn btn-secondary">Sign in free</Link>
              )}
            </div>
            <ul className="mt-5 flex flex-col">
              <Row ok>Every record, source, quote, coverage split and clip</Row>
              <Row ok><b className="font-semibold">{ASK.free} questions a day</b> with an account, {ASK.anon} without</Row>
              <Row ok>The standard model</Row>
              <Row ok={false} muted>Answers from this development only</Row>
              <Row ok={false} muted>Ask rests for the day when the free box is spent</Row>
            </ul>
          </article>
        </Reveal>

        <Reveal className="order-3" delay={80}>
          {founding ? (
            <article className="card flex flex-col p-6" aria-label="Founding member">
              <h2 className="text-[15px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-2)" }}>Founding member</h2>
              <p className="mt-3 flex items-baseline gap-1.5">
                <span className="font-record text-[40px] font-medium leading-none tracking-[-0.02em]">{rupees(founding.amount_paise)}</span>
                <span className="font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>/ year</span>
              </p>
              <p className="mt-1 h-5 font-mono text-[11px] tracking-[0.02em]" style={{ color: "var(--ink-3)" }}>{plans!.founding_left} of {FOUNDING_SEATS} seats · price locked 3 years</p>
              <div className="mt-5"><Action plan="founding" primary={false} label="Become a founding member" /></div>
              <ul className="mt-5 flex flex-col">
                <Row ok>Everything in Plus</Row>
                <Row ok>{rupees(founding.amount_paise)} a year, <b className="font-semibold">held for three years</b></Row>
                <Row ok>One of the first {FOUNDING_SEATS} readers who paid for an independent record</Row>
              </ul>
            </article>
          ) : (
            <article className="card flex flex-col p-6" aria-label="Founding member" style={{ borderStyle: "dashed", borderColor: "var(--line-strong)" }}>
              <h2 className="text-[15px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>Founding member</h2>
              <p className="mt-3 text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-3)" }}>{plans ? "All seats are taken. Thank you." : ""}</p>
            </article>
          )}
        </Reveal>
      </section>

      {note && <p className="mt-4 text-center text-[14px]" role="status" style={{ color: "var(--danger)" }}>{note}</p>}
      {onPlus && (
        <p className="mt-6 text-center text-[15px]" role="status">
          You&rsquo;re on Plus. Manage it from <Link href="/you" className="font-semibold underline underline-offset-4">your account</Link>.
        </p>
      )}

      {/* ── Side by side ──────────────────────────────────────────── */}
      <section className="mx-auto mt-16 max-w-[760px]" aria-labelledby="compare-title">
        <h2 id="compare-title" className="font-record text-[26px] font-medium leading-[1.2] tracking-[-0.01em]">Side by side</h2>
        <table className="mt-4 w-full border-collapse text-[14.5px] leading-[1.5]">
          <thead>
            <tr className="text-left text-[11.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>
              <th scope="col" className="border-b py-2 pr-3 font-semibold" style={{ borderColor: "var(--line-strong)" }}>What</th>
              <th scope="col" className="w-[26%] border-b py-2 pr-3 font-semibold" style={{ borderColor: "var(--line-strong)" }}>Free</th>
              <th scope="col" className="w-[26%] border-b py-2 font-semibold" style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}>Plus</th>
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
              <tr key={what} className="align-top">
                <th scope="row" className="border-b py-2.5 pr-3 text-left font-medium" style={{ borderColor: "var(--line)" }}>{what}</th>
                <td className="border-b py-2.5 pr-3" style={{ borderColor: "var(--line)", color: "var(--ink-2)" }}>{free}</td>
                <td className="border-b py-2.5 font-semibold" style={{ borderColor: "var(--line)" }}>{pl}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* ── Before you pay ─────────────────────────────────────────── */}
      <section className="mx-auto mt-16 max-w-[760px]" aria-labelledby="faq-title">
        <h2 id="faq-title" className="font-record text-[26px] font-medium leading-[1.2] tracking-[-0.01em]">Before you pay</h2>
        <div className="mt-2 border-t" style={{ borderColor: "var(--line)" }}>
          {FAQ.map((f) => (
            <details key={f.q} className="group border-b" style={{ borderColor: "var(--line)" }}>
              <summary className="flex min-h-[52px] cursor-pointer list-none items-center justify-between gap-4 py-3 text-[16px] font-medium">
                {f.q}
                <span className="font-mono text-[14px] transition-transform group-open:rotate-45" style={{ color: "var(--ink-3)" }} aria-hidden>+</span>
              </summary>
              <p className="pb-4 text-[15px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* ── One more time, and the small print ─────────────────────── */}
      {!onPlus && (
        <section className="mx-auto mt-16 max-w-[640px] text-center">
          <p className="font-record text-[24px] font-medium leading-[1.25]">A hundred questions a day, from the whole story.</p>
          <div className="mt-5 flex justify-center"><Action plan={period === "year" ? "plus_yearly" : "plus_monthly"} primary label={plus ? `Get Plus · ${rupees(plus.amount_paise)} ${period === "year" ? "a year" : "a month"}` : "Get Plus"} /></div>
        </section>
      )}
      <p className="mx-auto mt-10 max-w-[640px] text-center text-[13px] leading-[1.6]" style={{ color: "var(--ink-3)" }}>
        Payments by Razorpay · UPI Autopay, cards, net banking · GST included · cancel any time ·{" "}
        <Link href="/refunds" className="underline underline-offset-[3px]">Refund policy</Link> · <Link href="/terms" className="underline underline-offset-[3px]">Terms</Link>
      </p>
    </div>
  );
}
