"use client";

// Every change made from /admin, newest first, with the founder who made it
// (common/admin_audit). Read-only: the app never edits or deletes these rows.
// A timeline (admin charts, phase 5): grouped by IST day on a rail, each
// change in words with its code and details in mono, filterable by area.

import { useEffect, useState } from "react";

import { AdminSection, AdminTitle, useAdmin } from "@/components/admin/AdminShell";
import { dayLabel } from "@/components/admin/charts/format";
import { FilterSeg } from "@/components/admin/ui";
import { fetchAudit, type AuditEntry } from "@/lib/admin";

const ACTION_WORD: Record<string, string> = {
  "batch.explanations": "Edited a round's explanations",
  "batch.languages": "Filled in a batch's languages",
  "batch.list": "Changed a batch's listing",
  "batch.open": "Opened or closed a batch",
  "labeller.add": "Added a labeller",
  "labeller.grant": "Changed a qualification",
  "labeller.status": "Changed a labeller's status",
  "pipeline.run": "Asked the worker to collect",
};

type Area = "all" | "labeller" | "batch" | "pipeline";
const AREA_WORD: Record<Area, string> = { all: "All", labeller: "Labellers", batch: "Batches", pipeline: "Collection" };

const istDay = (iso: string) => new Date(iso).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
const istClock = (iso: string) => new Date(iso).toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit" });
const shown = (v: unknown) => (v !== null && typeof v === "object" ? JSON.stringify(v) : String(v));

export default function AuditPage() {
  const { session } = useAdmin();
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState("");
  const [area, setArea] = useState<Area>("all");

  useEffect(() => {
    fetchAudit(session)
      .then((r) => setEntries(r.entries))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load the audit log"));
  }, [session]);

  const all = entries ?? [];
  const inArea = (e: AuditEntry, a: Area) => a === "all" || e.action.startsWith(`${a}.`);
  const kept = all.filter((e) => inArea(e, area));
  // Newest first already; group consecutive entries by their IST day.
  const days = kept.reduce<Array<{ day: string; rows: AuditEntry[] }>>((acc, e) => {
    const day = istDay(e.created_at);
    const last = acc.at(-1);
    return last?.day === day ? [...acc.slice(0, -1), { day, rows: [...last.rows, e] }] : [...acc, { day, rows: [e] }];
  }, []);

  return (
    <>
      <AdminTitle>Audit</AdminTitle>
      {error && (
        <p role="alert" className="mt-5 text-[14px]" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}
      <AdminSection title="Changes made from this dashboard">
        {entries?.length === 0 && (
          <p className="text-[15px]" style={{ color: "var(--ink-2)" }}>
            Nothing yet. Every approval, pause, publish and listing made here will appear in this list.
          </p>
        )}
        {all.length > 0 && (
          <div className="mb-5">
            <FilterSeg
              label="Area"
              value={area}
              onChange={setArea}
              options={(["all", "labeller", "batch", "pipeline"] as const).map((a) => ({
                value: a,
                label: AREA_WORD[a],
                count: all.filter((e) => inArea(e, a)).length,
              }))}
            />
          </div>
        )}
        {days.map(({ day, rows }) => (
          <section key={day} aria-label={dayLabel(day)} className="mb-6">
            <h3 className="mb-2 flex items-baseline gap-2 text-[14px] font-semibold">
              {dayLabel(day)}
              <span className="font-mono text-[11px] font-normal tabular-nums" style={{ color: "var(--ink-3)" }}>
                {rows.length} {rows.length === 1 ? "CHANGE" : "CHANGES"}
              </span>
            </h3>
            <ol className="ml-[5px] border-l" style={{ borderColor: "var(--line-strong)" }}>
              {rows.map((e, i) => (
                <li key={`${e.created_at}-${i}`} className="relative pb-4 pl-5">
                  <span aria-hidden className="absolute -left-[5px] top-[7px] h-[9px] w-[9px] rounded-full" style={{ background: "var(--viz-1)", boxShadow: "0 0 0 2px var(--bg)" }} />
                  <p className="text-[15px]">
                    <span className="font-mono text-[12px] tabular-nums" style={{ color: "var(--ink-3)" }}>{istClock(e.created_at)}</span>{" "}
                    <span className="font-semibold">{ACTION_WORD[e.action] ?? e.action}</span>{" "}
                    <span style={{ color: "var(--ink-2)" }}>· {e.target}</span>
                  </p>
                  <p className="mt-0.5 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
                    {e.action} · {e.actor}
                    {Object.entries(e.detail ?? {}).map(([k, v]) => ` · ${k} ${shown(v)}`).join("")}
                  </p>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </AdminSection>
    </>
  );
}
