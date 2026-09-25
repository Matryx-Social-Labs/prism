/**
 * One change made from /admin (common/admin_audit), as the design's AuditItem:
 * the IST time in mono, what was done in words and to what, then its code,
 * the founder and the details in mono.
 */

import type { AuditEntry } from "@/lib/admin";

/** Each audit code in a founder's words. */
export const ACTION_WORD: Record<string, string> = {
  "batch.explanations": "Edited a round's explanations",
  "batch.languages": "Filled in a batch's languages",
  "batch.list": "Changed a batch's listing",
  "batch.open": "Opened or closed a batch",
  "labeller.add": "Added a labeller",
  "labeller.grant": "Changed a qualification",
  "labeller.status": "Changed a labeller's status",
  "pipeline.run": "Asked the worker to collect",
};

export const istDay = (iso: string) => new Date(iso).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
export const istClock = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", hour12: false });
const shown = (v: unknown) => (v !== null && typeof v === "object" ? JSON.stringify(v) : String(v));

export function AuditItem({ entry: e }: { entry: AuditEntry }) {
  return (
    <li className="grid grid-cols-[52px_minmax(0,1fr)] gap-3 border-t py-3 sm:grid-cols-[64px_minmax(0,1fr)]" style={{ borderColor: "var(--line)" }}>
      <span className="font-mono text-[12px] tabular-nums" style={{ color: "var(--ink-2)" }}>
        {istClock(e.created_at)}
      </span>
      <div className="grid min-w-0 gap-[3px]">
        <p className="text-[14.5px] font-medium leading-[1.35] [overflow-wrap:anywhere]">
          {ACTION_WORD[e.action] ?? e.action} <span style={{ color: "var(--ink-2)" }}>· {e.target}</span>
        </p>
        <p className="flex flex-wrap gap-x-2.5 font-mono text-[11.5px] [overflow-wrap:anywhere]" style={{ color: "var(--ink-3)" }}>
          <span>{e.action}</span>
          <span>{e.actor}</span>
          {Object.entries(e.detail ?? {}).map(([k, v]) => (
            <span key={k}>
              {k} {shown(v)}
            </span>
          ))}
        </p>
      </div>
    </li>
  );
}
