"use client";

// Every change made from /admin, newest first, with the founder who made it
// (common/admin_audit). Read-only: the app never edits or deletes these rows.
// Grouped by IST day, each day under its rule with a count; each change an
// AuditItem (the time, in words what and to what, then the code, the founder
// and the details in mono); filterable by area. Only the newest are loaded,
// and the line under the title says so when the list may run on.

import { useEffect, useState } from "react";

import { AdminHead, AdminSection, Quiet, useAdmin } from "@/components/admin/AdminShell";
import { AuditItem, istDay } from "@/components/admin/AuditItem";
import { FilterSwitch } from "@/components/admin/ui";
import { Alert } from "@/components/ui";
import { fetchAudit, type AuditEntry } from "@/lib/admin";

type Area = "all" | "labeller" | "batch" | "pipeline";
const AREA_WORD: Record<Area, string> = { all: "All", labeller: "Labellers", batch: "Batches", pipeline: "Collection" };
const LIMIT = 100;

/** "Thu 24 Sept · IST" for an IST calendar day (YYYY-MM-DD). */
const dayTitle = (day: string) =>
  `${new Date(`${day}T12:00:00+05:30`).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", weekday: "short", day: "numeric", month: "short" }).replace(",", "")} · IST`;

export default function AuditPage() {
  const { session } = useAdmin();
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState("");
  const [area, setArea] = useState<Area>("all");

  useEffect(() => {
    fetchAudit(session, LIMIT)
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
      <AdminHead title="Audit" line={entries && entries.length >= LIMIT ? `NEWEST ${LIMIT} CHANGES` : null} />
      {error && <Alert tone="error">{error}</Alert>}
      {entries?.length === 0 && <Quiet>Nothing yet. Every approval, pause, publish and listing made here will appear in this list.</Quiet>}
      {all.length > 0 && (
        <FilterSwitch
          label="Area"
          value={area}
          onChange={setArea}
          options={(["all", "labeller", "batch", "pipeline"] as const).map((a) => ({ value: a, label: AREA_WORD[a], count: all.filter((e) => inArea(e, a)).length }))}
        />
      )}
      {all.length > 0 && kept.length === 0 && <Quiet>No changes in this area.</Quiet>}
      {days.map(({ day, rows }) => (
        <AdminSection key={day} title={dayTitle(day)} sub={`${rows.length} ${rows.length === 1 ? "CHANGE" : "CHANGES"}`}>
          <ul>
            {rows.map((e, i) => (
              <AuditItem key={`${e.created_at}-${i}`} entry={e} />
            ))}
          </ul>
        </AdminSection>
      ))}
    </>
  );
}
