"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight } from "@/components/icons";
import { SectionHead } from "@/components/SectionHead";
import { PLAN_LABEL } from "@/components/PlanCard";
import { fetchPayments, rupees, type Payment } from "@/lib/billing";
import { billingDay } from "@/lib/dateline";
import type { Session } from "@/lib/session";

/**
 * Every charge on the account, newest first, on hairlines (DESIGN.md
 * § Account): the date in mono, the plan, the amount in tabular mono, the
 * state as a word, and Razorpay's own invoice — view or download as PDF —
 * behind "Invoice". Read live from Razorpay, so it never disagrees with the
 * receipt in the reader's inbox. Renders nothing for a reader who has never
 * paid; the section only exists when there is something in it.
 */
const when = (iso: string | null) => (iso ? billingDay(iso) : "—");

export function Payments({ session }: { session: Session }) {
  const [rows, setRows] = useState<Payment[] | null | undefined>(undefined);
  useEffect(() => {
    fetchPayments(session.token).then(setRows).catch(() => setRows(null));
  }, [session.token]);

  if (rows === undefined || (rows && rows.length === 0)) return null;
  return (
    <section aria-labelledby="payments-title">
      <SectionHead id="payments-title" title="Payments" count={rows?.length} hint="Each invoice is Razorpay's; open it to download the PDF." />
      {rows === null ? (
        <p className="p-alert" role="status">Razorpay could not be reached just now. The receipts in your inbox are the same documents; try again in a minute.</p>
      ) : (
        <ol>
          {/* money/PaymentRow: date · plan · amount + state · invoice on a desk; plan and amount lead on the phone. */}
          {rows.map((p) => (
            <li key={p.invoice_id ?? `${p.paid_at}-${p.amount_paise}`} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 py-3 sm:grid-cols-[124px_minmax(0,1fr)_auto_auto]" style={{ borderTop: "1px solid var(--line)", font: "400 14px/1.3 var(--font-read)" }}>
              <span className="order-3 font-mono text-[12px] tabular-nums sm:order-none" style={{ color: "var(--ink-2)" }}>{when(p.paid_at)}</span>
              <span className="order-1 min-w-0 sm:order-none">{PLAN_LABEL[p.plan] ?? "Plus"}</span>
              <span className="order-2 flex items-center gap-1.5 justify-self-end font-mono text-[12.5px] tabular-nums sm:order-none">
                {rupees(p.amount_paise)}
                <span className="p-tag-mono uppercase" style={{ borderStyle: p.status === "refunded" ? "dashed" : "solid" }}>{p.status}</span>
              </span>
              {p.invoice_url ? (
                <a href={p.invoice_url} target="_blank" rel="noopener noreferrer" className="p-link order-4 inline-flex min-h-[44px] items-center gap-1 justify-self-end text-[13px] sm:order-none sm:min-h-0">
                  Invoice <ArrowUpRight size={13} />
                </a>
              ) : (
                <span className="order-4 justify-self-end font-mono text-[11px] sm:order-none" style={{ color: "var(--ink-3)" }}>—</span>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
