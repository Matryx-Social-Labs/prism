"use client";

/**
 * The founders' desk: what needs you, then the ledger — visits, sign-ups,
 * engagement, money, demand and supply for a period against the one before,
 * every figure with where it was counted (common/metrics.py; design direction
 * "The ledger", DESIGN.md). One primary action is not the point of this page;
 * the period switch and the CSV are secondary on purpose.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AdminTitle, useAdmin } from "@/components/admin/AdminShell";
import { LedgerSection, dayLabel } from "@/components/admin/Ledger";
import { downloadWeeklyCsv, fetchBatches, fetchLabellers, fetchMetrics, type Metrics } from "@/lib/admin";

const PERIODS = [7, 28, 90] as const;

interface Need {
  href: string;
  count: number;
  text: string;
}

export default function AdminOverview() {
  const { session } = useAdmin();
  const [days, setDays] = useState<(typeof PERIODS)[number]>(28);
  const [data, setData] = useState<Metrics | null>(null);
  const [needs, setNeeds] = useState<Need[] | null>(null);
  const [needsFailed, setNeedsFailed] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      setData(await fetchMetrics(session, days));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the numbers");
    }
  }, [session, days]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    // What is waiting on a founder, from the same routes the pages below use.
    Promise.all([fetchLabellers(session), fetchBatches(session)])
      .then(([l, b]) =>
        setNeeds([
          { href: "/admin/labellers", count: l.labellers.filter((x) => x.status === "applied").length, text: "applications to read" },
          { href: "/admin/batches", count: b.batches.filter((x) => x.purpose !== "work" && !x.open).length, text: "practice rounds or tests not published" },
          { href: "/admin/batches", count: b.batches.filter((x) => x.purpose === "work" && x.gated < x.tasks).length, text: "work batches without a language gate" },
        ]),
      )
      // Never "nothing is waiting" when we could not look.
      .catch(() => setNeedsFailed(true));
  }, [session]);

  const csv = async () => {
    try {
      await downloadWeeklyCsv(session);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not download the CSV");
    }
  };

  const open = needs?.filter((n) => n.count > 0) ?? [];

  return (
    <>
      <div className="mt-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <AdminTitle>Overview</AdminTitle>
          {data && (
            <p className="mt-2 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
              {dayLabel(data.range.start).toUpperCase()} – {dayLabel(data.range.end).toUpperCase()} · IST
              {data.counting_since.usage
                ? ` · VISITS COUNTED SINCE ${dayLabel(data.counting_since.usage).toUpperCase()}`
                : " · NO VISITS COUNTED YET"}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="seg" role="tablist" aria-label="Period">
            {PERIODS.map((p) => (
              <button key={p} type="button" role="tab" aria-selected={days === p} onClick={() => setDays(p)}>
                {p} days
              </button>
            ))}
          </div>
          <button type="button" className="btn btn-secondary" onClick={() => void csv()}>
            Weekly CSV
          </button>
        </div>
      </div>

      {error && (
        <p role="alert" className="mt-5 text-[14px]" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}

      <section className="mt-8 border-t pt-4" style={{ borderColor: "var(--line-strong)" }} aria-labelledby="needs-you">
        <h2 id="needs-you" className="text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>
          Needs you
        </h2>
        {needsFailed && (
          <p className="mt-2 text-[15px]" style={{ color: "var(--danger)" }}>Could not check what is waiting. Reload to try again.</p>
        )}
        {needs && open.length === 0 && (
          <p className="mt-2 text-[15px]" style={{ color: "var(--ink-2)" }}>Nothing is waiting on you.</p>
        )}
        <ul className="mt-1 flex flex-wrap gap-x-8 gap-y-2">
          {open.map((n) => (
            <li key={n.text}>
              <Link href={n.href} className="inline-flex min-h-[44px] items-baseline gap-2 underline-offset-4 hover:underline" style={{ color: "var(--accent)" }}>
                <span className="font-mono text-[17px] tabular-nums">{n.count}</span>{" "}
                <span className="text-[15px]">{n.text}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      {data?.sections.map((s) => <LedgerSection key={s.key} section={s} start={data.range.start} />)}
    </>
  );
}
