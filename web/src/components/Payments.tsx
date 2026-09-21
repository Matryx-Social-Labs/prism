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
    <section className="mt-8" aria-labelledby="payments-title">
      <SectionHead id="payments-title" title="Payments" count={rows?.length} hint="Each invoice is Razorpay's; open it to download the PDF." />
      {rows === null ? (
        <div className="card" role="status">
          <p className="text-[14.5px]" style={{ color: "var(--ink-2)" }}>Razorpay could not be reached just now. The receipts in your inbox are the same documents; try again in a minute.</p>
        </div>
      ) : (
        <ol className="card divide-y p-0" style={{ borderColor: "var(--line)" }}>
          {rows.map((p) => (
            <li key={p.invoice_id ?? `${p.paid_at}-${p.amount_paise}`} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3" style={{ borderColor: "var(--line)" }}>
              <span className="font-mono text-[12px] tabular-nums" style={{ color: "var(--ink-3)" }}>{when(p.paid_at)}</span>
              <span className="min-w-0 flex-1 text-[14.5px]">{PLAN_LABEL[p.plan] ?? "Plus"}</span>
              <span className="font-mono text-[12.5px] tabular-nums">{rupees(p.amount_paise)}</span>
              <span className="font-mono text-[11px] uppercase tracking-[0.03em]" style={{ color: p.status === "refunded" ? "var(--ink)" : "var(--ink-3)" }}>{p.status}</span>
              {p.invoice_url ? (
                <a href={p.invoice_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[13.5px] font-semibold underline-offset-[3px] hover:underline" style={{ color: "var(--accent)" }}>
                  Invoice <ArrowUpRight size={13} />
                </a>
              ) : (
                <span className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>—</span>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
