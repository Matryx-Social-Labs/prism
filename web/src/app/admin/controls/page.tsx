"use client";

/**
 * The switches, read-only, the one control — ask the worker to collect now —
 * and today's changes from the audit log.
 * Founder decision D4 (2026-09-23): flags are shown, never set, from here —
 * setting them would move them out of the environment and change how a bad
 * change is rolled back. The values are this API's own view; the worker reads
 * its own environment, which is how a feature runs in shadow there first.
 *
 * Each switch is a SwitchRow: ON solid ink, OFF on a dashed edge — a word, and
 * nothing that looks like it could be flipped. Numbers are listed apart.
 */

import { useEffect, useState } from "react";

import { AdminSection, AdminTitle, Quiet, useAdmin } from "@/components/admin/AdminShell";
import { AuditItem, istDay } from "@/components/admin/AuditItem";
import { fetchAudit, fetchFlags, triggerCollection, type AuditEntry, type Flag } from "@/lib/admin";

export default function ControlsPage() {
  const { session } = useAdmin();
  const [flags, setFlags] = useState<Flag[] | null>(null);
  const [audit, setAudit] = useState<AuditEntry[] | null>(null);
  const [auditFailed, setAuditFailed] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchFlags(session)
      .then((r) => setFlags(r.flags))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load the switches"));
  }, [session]);

  useEffect(() => {
    fetchAudit(session, 50)
      .then((r) => setAudit(r.entries))
      .catch(() => setAuditFailed(true));
  }, [session]);

  const collecting = flags?.find((f) => f.name === "PRISM_INGESTION_ENABLED")?.value;
  const switches = flags?.filter((f) => typeof f.value === "boolean") ?? [];
  const numbers = flags?.filter((f) => typeof f.value === "number") ?? [];
  const today = istDay(new Date().toISOString());
  const todays = audit?.filter((e) => istDay(e.created_at) === today) ?? [];

  const collect = async () => {
    if (!window.confirm("Ask the worker to collect new reports now? It is recorded against you.")) return;
    setSending(true);
    setError("");
    try {
      const r = await triggerCollection(session);
      setNote(r.collecting ? "Asked. The worker collects on its next read of the queue." : "Asked — but collection is switched off, so the worker will not collect.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "The request was refused");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="max-w-[760px]">
      <AdminTitle>Controls</AdminTitle>
      {error && (
        <p role="alert" className="p-alert p-alert--error mt-5">
          {error}
        </p>
      )}

      <div className="admin-panel mt-6 flex flex-wrap items-center gap-3">
        <div className="min-w-0 flex-1 basis-[240px]">
          <h2 className="text-[15px] font-semibold leading-[1.3]">Collect now</h2>
          <p className="text-[14px] leading-[1.5]" style={{ color: "var(--ink-2)" }}>
            Collection runs on its own schedule. This asks the worker to run it once now. Recorded in the audit log.
          </p>
          {note && (
            <p aria-live="polite" className="mt-2 text-[14px]" style={{ color: "var(--ink)" }}>
              {note}
            </p>
          )}
        </div>
        <button type="button" className="p-btn p-btn--secondary" disabled={sending || collecting === undefined} onClick={() => void collect()}>
          Collect now
        </button>
      </div>

      <AdminSection
        title="Switches"
        sub={switches.length ? `${switches.filter((f) => f.value).length} of ${switches.length} on · read-only, as the API sees them` : undefined}
        hint="Changed in Railway's environment, not here; the worker has its own copy."
      >
        <ul>
          {switches.map((f) => (
            <FlagRow key={f.name} f={f}>
              <span
                className="p-tag-mono"
                style={f.value ? { background: "var(--ink)", color: "var(--paper)", borderColor: "var(--ink)" } : { borderStyle: "dashed" }}
              >
                {f.value ? "ON" : "OFF"}
              </span>
            </FlagRow>
          ))}
        </ul>
      </AdminSection>

      {numbers.length > 0 && (
        <AdminSection title="Limits">
          <ul>
            {numbers.map((f) => (
              <FlagRow key={f.name} f={f}>
                <span className="font-mono text-[14px] tabular-nums" style={{ color: "var(--ink)" }}>
                  {f.value.toLocaleString("en-IN")}
                </span>
              </FlagRow>
            ))}
          </ul>
        </AdminSection>
      )}

      <AdminSection title="Audit · today" sub={audit ? `${todays.length} ${todays.length === 1 ? "change" : "changes"}` : undefined}>
        {auditFailed && <p className="p-alert p-alert--error">Could not load today&apos;s changes. This is not the same as none.</p>}
        {audit && todays.length === 0 && <Quiet>Nothing was changed from this dashboard today.</Quiet>}
        <ul>
          {todays.map((e, i) => (
            <AuditItem key={`${e.created_at}-${i}`} entry={e} />
          ))}
        </ul>
      </AdminSection>
    </div>
  );
}

/** SwitchRow: what the setting does, its name in mono, its state at the end. */
function FlagRow({ f, children }: { f: Flag; children: React.ReactNode }) {
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-t py-3" style={{ borderColor: "var(--line)" }}>
      <span className="min-w-0">
        <span className="block text-[14.5px] font-medium leading-[1.35]" style={{ color: "var(--ink)" }}>{f.does}</span>
        <span className="block font-mono text-[11.5px] [overflow-wrap:anywhere]" style={{ color: "var(--ink-3)" }}>{f.name}</span>
      </span>
      {children}
    </li>
  );
}
