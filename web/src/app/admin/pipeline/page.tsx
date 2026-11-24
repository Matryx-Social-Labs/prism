"use client";

/**
 * How long the pipeline's steps take, per UTC day (api/routes/admin_metrics.py).
 * Timings are histograms, so p50 and p95 are a bucket's upper bound: "≤ 700 ms"
 * means at most that. A day nothing was recorded reads "not recorded", not 0;
 * a sweeper queue that could not be read reads "not available".
 */

import { useEffect, useState } from "react";

import { AdminHead, AdminSection, Quiet, useAdmin } from "@/components/admin/AdminShell";
import { DataTable } from "@/components/admin/charts/ChartPanel";
import { Alert, EmptyState } from "@/components/ui";
import { bound, duration, fetchPipeline, istTime, type Pipeline, type PipelineDay } from "@/lib/admin";

const DAYS = 7;

const TIMING_LABEL: Record<string, string> = {
  "match_lock.wait": "Match lock — waiting",
  "match_lock.held": "Match lock — held",
  "jev.event-verify": "Judge call — same record?",
  "jev.story-verify": "Judge call — same story?",
  "jev.event-escalate": "Judge call — second opinion",
  "analysis.queue_age": "Analysis queue — time past due",
};

function Day({ day, children }: { day: PipelineDay; children: React.ReactNode }) {
  return (
    <div role="group" aria-label={day.day} className="grid gap-1.5">
      <h3 className="p-count">{day.day}</h3>
      {day.recorded ? children : <Quiet>not recorded</Quiet>}
    </div>
  );
}

function sweeperLine(sweeper: Pipeline["sweeper"]): string {
  if (!sweeper) return "not available";
  const age = sweeper.oldest_due_age_s;
  return age === null ? `${sweeper.due} due` : `${sweeper.due} due · oldest ${duration(age * 1000)}`;
}

export default function PipelinePage() {
  const { session } = useAdmin();
  const [data, setData] = useState<Pipeline | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let current = true;
    setError("");
    fetchPipeline(session, DAYS)
      .then((d) => current && setData(d))
      .catch((e: unknown) => current && setError(e instanceof Error ? e.message : "Could not load the pipeline"));
    return () => {
      current = false;
    };
  }, [session]);

  const recorded = data?.days.filter((d) => d.recorded) ?? [];
  const hours = [...(data?.throughput ?? [])].sort((a, b) => b.hour.localeCompare(a.hour));
  const newest = hours[0];
  const empty = recorded.length === 0 && hours.length === 0;

  return (
    <>
      <AdminHead title="Pipeline" line={`How long each step takes · per UTC day · last ${DAYS} days`.toUpperCase()} />
      {error && <Alert tone="error">{error}</Alert>}

      {data && empty && (
        <EmptyState title="Nothing recorded yet">
          Timings and counts start with the first article the pipeline handles after they shipped. Earlier days are not counted here.
        </EmptyState>
      )}

      {data && (
        <AdminSection title="Now" sub="SWEEPER QUEUE · NEWEST HOUR">
          <DataTable
            table={{
              columns: ["", "Value"],
              rows: [
                ["Sweeper", sweeperLine(data.sweeper)],
                [
                  newest ? `Newest hour · ${istTime(newest.hour)} IST` : "Newest hour",
                  newest
                    ? `${newest.observed} observed · ${newest.classified} classified · ${newest.enriched} enriched · ${newest.correlated} correlated`
                    : "no hours recorded",
                ],
              ],
            }}
          />
        </AdminSection>
      )}

      {data && recorded.length > 0 && (
        <>
          <AdminSection title="Timings by day" sub="UTC DAY · COUNT · P50 · P95 · UPPER BOUNDS">
            {data.days.map((d) => (
              <Day key={d.day} day={d}>
                {d.timings.length ? (
                  <DataTable
                    table={{
                      columns: ["Measure", "Count", "p50", "p95"],
                      rows: d.timings.map((t) => [TIMING_LABEL[t.name] ?? t.name, t.n, bound(t.p50_ms), bound(t.p95_ms)]),
                    }}
                  />
                ) : (
                  <Quiet>none</Quiet>
                )}
              </Day>
            ))}
          </AdminSection>
          <AdminSection title="Counters by day" sub="UTC DAY · NAME · COUNT">
            {data.days.map((d) => (
              <Day key={d.day} day={d}>
                {d.counters.length ? (
                  <DataTable table={{ columns: ["Counter", "Count"], rows: d.counters.map((c) => [c.name, c.n]) }} />
                ) : (
                  <Quiet>none</Quiet>
                )}
              </Day>
            ))}
          </AdminSection>
        </>
      )}

      {data && !empty && (
        <AdminSection title="Articles per hour, last 24 hours" sub="IST HOUR · NEWEST FIRST">
          {hours.length ? (
            <DataTable
              table={{
                columns: ["Hour (IST)", "Observed", "Classified", "Enriched", "Correlated"],
                rows: hours.map((h) => [istTime(h.hour), h.observed, h.classified, h.enriched, h.correlated]),
              }}
            />
          ) : (
            <Quiet>No hours recorded in the last 24 hours.</Quiet>
          )}
        </AdminSection>
      )}
    </>
  );
}
