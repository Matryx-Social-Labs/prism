"use client";

/**
 * The founders' desk: what needs you, eight headline numbers, then each area
 * drawn as charts — supply first (it has the longest record), then visits,
 * sign-ups, engagement, money and demand, each against the period before
 * (common/metrics.py; founder decisions V1–V5, 2026-09-24). Where a number was
 * counted sits behind its ⓘ; every chart turns into its table.
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { AdminTitle, useAdmin } from "@/components/admin/AdminShell";
import { KpiTile } from "@/components/admin/charts/KpiTile";
import { dayLabel } from "@/components/admin/charts/format";
import { DashboardSection } from "@/components/admin/Dashboard";
import { downloadWeeklyCsv, fetchBatches, fetchLabellers, fetchMetrics, type MetricRow, type Metrics } from "@/lib/admin";

const PERIODS = [7, 28, 90] as const;

/** The headline row: [section, measure]. */
const HEADLINE: ReadonlyArray<[string, string]> = [
  ["visits", "visitor_days"],
  ["signups", "new_accounts"],
  ["engagement", "active_accounts"],
  ["engagement", "questions"],
  ["money", "paying"],
  ["money", "mrr"],
  ["supply", "reports"],
  ["supply", "events"],
];

/** Supply first: it is counted since launch, so it is the fullest picture. */
const ORDER = ["supply", "visits", "signups", "engagement", "money", "demand"];

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

  useEffect(() => {
    // A slow 90-day answer must not land over the 7 days asked for after it.
    let current = true;
    setError("");
    fetchMetrics(session, days)
      .then((d) => current && setData(d))
      .catch((e: unknown) => current && setError(e instanceof Error ? e.message : "Could not load the numbers"));
    return () => {
      current = false;
    };
  }, [session, days]);

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
  const find = (section: string, key: string): MetricRow | undefined =>
    data?.sections.find((x) => x.key === section)?.rows.find((r) => r.key === key);
  const headline = HEADLINE.map(([sec, key]) => find(sec, key)).filter((r): r is MetricRow => !!r);
  const sections = data ? [...data.sections].sort((a, b) => ORDER.indexOf(a.key) - ORDER.indexOf(b.key)) : [];

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

      {headline.length > 0 && (
        <div className="mt-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {headline.map((r) => (
            <KpiTile
              key={r.key}
              label={r.label}
              current={r.current}
              previous={r.previous}
              series={r.series}
              unit={r.unit}
              source={r.source}
              note={r.note}
            />
          ))}
        </div>
      )}

      {data && sections.map((s) => <DashboardSection key={s.key} section={s} start={data.range.start} />)}
    </>
  );
}
