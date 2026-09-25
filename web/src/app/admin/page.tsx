"use client";

/**
 * The founders' desk: what needs you, eight headline numbers, then each area
 * drawn as charts — supply first (it has the longest record), then visits,
 * sign-ups, engagement, money and demand, each against the period before
 * (common/metrics.py; founder decisions V1–V5, 2026-09-24). Where a number was
 * counted opens under its ⓘ; every chart turns into its table.
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { AdminHead, useAdmin } from "@/components/admin/AdminShell";
import { ArrowRight } from "@/components/icons";
import { KpiTile } from "@/components/admin/charts/KpiTile";
import { dayLabel } from "@/components/admin/charts/format";
import { DashboardSection } from "@/components/admin/Dashboard";
import { Alert } from "@/components/ui";
import { downloadWeeklyCsv, fetchBatches, fetchLabellers, fetchMetrics, type MetricRow, type Metrics } from "@/lib/admin";

const PERIODS = [7, 28, 90] as const;

/** The headline row: [section, measure, the counting start that explains a
 *  missing period before]. Money keeps no history, so it has none to explain. */
const HEADLINE: ReadonlyArray<[string, string, keyof Metrics["counting_since"] | null]> = [
  ["visits", "visitor_days", "usage"],
  ["signups", "new_accounts", null],
  ["engagement", "active_accounts", "active"],
  ["engagement", "questions", null],
  ["money", "paying", null],
  ["money", "mrr", null],
  ["supply", "reports", null],
  ["supply", "events", null],
];

/** Supply first: it is counted since launch, so it is the fullest picture. */
const ORDER = ["supply", "visits", "signups", "engagement", "money", "demand"];

const year = (iso: string) => iso.slice(0, 4);

/** "28 AUG – 24 SEP 2026 IST · VISIT COUNTING BEGAN 12 SEP": real dates only. */
function periodLine({ range, counting_since }: Metrics): string {
  const { start, end } = range;
  const span = year(start) === year(end) ? `${dayLabel(start)} – ${dayLabel(end)} ${year(end)}` : `${dayLabel(start)} ${year(start)} – ${dayLabel(end)} ${year(end)}`;
  const usage = counting_since.usage;
  const visits = usage ? `VISIT COUNTING BEGAN ${dayLabel(usage)}${year(usage) === year(end) ? "" : ` ${year(usage)}`}` : "NO VISITS COUNTED YET";
  return `${span} IST · ${visits}`.toUpperCase();
}

/** The visits section's provenance: from when visits were counted. */
function visitsSub({ range, counting_since }: Metrics): string | undefined {
  const u = counting_since.usage;
  if (!u) return "NOT COUNTED YET";
  if (u === range.end) return "COUNTING BEGAN TODAY";
  return u > range.start ? `COUNTED FROM ${dayLabel(u).toUpperCase()} · EARLIER DAYS HATCHED` : undefined;
}

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

  const find = (section: string, key: string): MetricRow | undefined =>
    data?.sections.find((x) => x.key === section)?.rows.find((r) => r.key === key);
  const headline = HEADLINE.flatMap(([sec, key, since]) => {
    const row = find(sec, key);
    return row ? [{ row, since: since && data ? data.counting_since[since] : null }] : [];
  });
  const sections = data ? [...data.sections].sort((a, b) => ORDER.indexOf(a.key) - ORDER.indexOf(b.key)) : [];

  return (
    <>
      <AdminHead title="Overview" line={data && periodLine(data)}>
        <div className="p-seg" role="tablist" aria-label="Period">
          {PERIODS.map((p) => (
            <button key={p} type="button" role="tab" aria-selected={days === p} onClick={() => setDays(p)}>
              {p} days
            </button>
          ))}
        </div>
        <button type="button" className="p-btn p-btn--secondary p-btn--sm p-hit" onClick={() => void csv()}>
          Weekly CSV
        </button>
      </AdminHead>

      {error && <Alert tone="error">{error}</Alert>}

      <section aria-labelledby="needs-you">
        <h2 id="needs-you" className="p-eyebrow mb-2">
          Needs you
        </h2>
        <NeedsYou needs={needs} failed={needsFailed} />
      </section>

      {headline.length > 0 && (
        <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
          {headline.map(({ row: r, since }) => (
            <KpiTile
              key={r.key}
              label={r.label}
              current={r.current}
              previous={r.previous}
              series={r.series}
              unit={r.unit}
              source={r.source}
              note={r.note}
              countedSince={since}
            />
          ))}
        </div>
      )}

      {data && sections.map((s) => <DashboardSection key={s.key} section={s} start={data.range.start} sub={s.key === "visits" ? visitsSub(data) : undefined} />)}
    </>
  );
}

/** What is waiting on a founder, each a link to where it is done. Could not
 *  look is never "nothing": it says so, apart from an empty list. */
function NeedsYou({ needs, failed }: { needs: Need[] | null; failed: boolean }) {
  if (failed) {
    return (
      <p className="p-alert p-alert--error">Could not check what is waiting on you. This is not the same as nothing. Reload to try again.</p>
    );
  }
  if (!needs) return null;
  const open = needs.filter((n) => n.count > 0);
  if (!open.length) return <p className="p-alert p-alert--info">Nothing is waiting on you.</p>;
  return (
    <ul className="grid gap-1.5">
      {open.map((n) => (
        <li key={n.text}>
          <Link
            href={n.href}
            className="flex min-h-[44px] items-baseline gap-2.5 rounded-[var(--r-md)] border px-3 py-2.5 no-underline hover:bg-[var(--sunken)]"
            style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}
          >
            <span className="font-mono text-[13px] font-medium tabular-nums">{n.count}</span>{" "}
            <span className="min-w-0 flex-1 text-[14px] font-medium leading-[1.35]">{n.text}</span>
            <ArrowRight size={14} className="shrink-0 self-center text-[var(--accent)]" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
