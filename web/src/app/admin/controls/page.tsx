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
 * Collect now is asked in place before it is sent, and says what happened:
 * asked (with the time and the audit code), or asked while collection is off.
 */

import { useEffect, useState } from "react";

import { AdminSection, AdminTitle, Quiet, useAdmin } from "@/components/admin/AdminShell";
import { AuditItem, istClock, istDay } from "@/components/admin/AuditItem";
import { dayLabel } from "@/components/admin/charts/format";
import { Confirm, SwitchRow } from "@/components/admin/ui";
import { Alert } from "@/components/ui";
import { fetchAudit, fetchFlags, triggerCollection, type AuditEntry, type Flag } from "@/lib/admin";

const COLLECT_FLAG = "PRISM_INGESTION_ENABLED";
const stamp = (iso: string) => `${dayLabel(iso)} ${istClock(iso)} IST`;

type Asked = { at: string; collecting: boolean };

export default function ControlsPage() {
  const { session, email } = useAdmin();
  const [flags, setFlags] = useState<Flag[] | null>(null);
  const [audit, setAudit] = useState<AuditEntry[] | null>(null);
  const [auditFailed, setAuditFailed] = useState(false);
  const [error, setError] = useState("");
  const [asking, setAsking] = useState(false);
  const [asked, setAsked] = useState<Asked | null>(null);
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
  }, [session, asked]);

  const known = flags?.some((f) => f.name === COLLECT_FLAG);
  const switches = flags?.filter((f) => typeof f.value === "boolean") ?? [];
  const numbers = flags?.filter((f) => typeof f.value === "number") ?? [];
  const today = istDay(new Date().toISOString());
  const todays = audit?.filter((e) => istDay(e.created_at) === today) ?? [];
  const lastAsked = audit?.find((e) => e.action === "pipeline.run");

  const collect = async () => {
    setSending(true);
    setError("");
    try {
      const r = await triggerCollection(session);
      setAsked({ at: new Date().toISOString(), collecting: r.collecting });
      setAsking(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "The request was refused");
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <AdminTitle>Controls</AdminTitle>
      {error && <Alert tone="error">{error}</Alert>}

      <section className="admin-panel grid gap-2.5" aria-labelledby="collect-now">
        <div className="flex flex-wrap items-center gap-3">
          <div className="min-w-0 flex-[1_1_260px]">
            <h2 id="collect-now" className="text-[15px] font-semibold leading-[1.3]">
              Collect now
            </h2>
            <p className="text-[14px] leading-[1.5]" style={{ color: "var(--ink-2)" }}>
              Asks the worker to collect new reports now, outside its schedule. Recorded in the audit log.
              {lastAsked && ` Last asked ${stamp(lastAsked.created_at)} by ${lastAsked.actor}.`}
            </p>
          </div>
          {!asking && !asked && (
            <button type="button" className="p-btn p-btn--secondary" disabled={sending || !known} onClick={() => setAsking(true)}>
              Collect now
            </button>
          )}
        </div>
        {asking && (
          <Confirm yes="Yes, collect" no="Not now" busy={sending} onYes={() => void collect()} onNo={() => setAsking(false)}>
            Ask the worker to collect new reports now? It is recorded against you.
          </Confirm>
        )}
        {asked?.collecting && (
          <p aria-live="polite" className="font-mono text-[11.5px] [overflow-wrap:anywhere]" style={{ color: "var(--ink-3)" }}>
            ASKED AT {istClock(asked.at)} IST · RECORDED AS pipeline.run BY {email}
          </p>
        )}
        {asked && !asked.collecting && (
          <Alert tone="info" title="Collection is switched off">
            {COLLECT_FLAG} is OFF as the API sees it, so the worker will not collect. The request is recorded in the audit log.
          </Alert>
        )}
      </section>

      <AdminSection
        title="Switches"
        sub={switches.length ? `${switches.filter((f) => f.value).length} OF ${switches.length} ON · READ-ONLY, AS THE API SEES THEM` : undefined}
        hint="Changed in Railway's environment, not here; the worker has its own copy."
      >
        <ul>
          {switches.map((f) => (
            <SwitchRow key={f.name} name={f.name} does={f.does} on={f.value === true} />
          ))}
        </ul>
      </AdminSection>

      {numbers.length > 0 && (
        <AdminSection title="Limits" sub="NUMBERS, LISTED APART">
          <div className="min-w-0 overflow-x-auto">
            <table className="p-table">
              <thead>
                <tr>
                  <th scope="col">Limit</th>
                  <th scope="col">Name</th>
                  <th scope="col" className="num">
                    Value
                  </th>
                </tr>
              </thead>
              <tbody>
                {numbers.map((f) => (
                  <tr key={f.name}>
                    <td style={{ color: "var(--ink)" }}>{f.does}</td>
                    <td className="font-mono text-[11.5px] [overflow-wrap:anywhere]" style={{ color: "var(--ink-3)" }}>
                      {f.name}
                    </td>
                    <td className="num" style={{ color: "var(--ink)" }}>
                      {f.value.toLocaleString("en-IN")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </AdminSection>
      )}

      <AdminSection title="Audit · today" sub={audit ? `${todays.length} ${todays.length === 1 ? "CHANGE" : "CHANGES"}` : undefined}>
        {auditFailed && <Alert tone="error">Could not load today&apos;s changes. This is not the same as none.</Alert>}
        {audit && todays.length === 0 && <Quiet>Nothing was changed from this dashboard today.</Quiet>}
        <ul>
          {todays.map((e, i) => (
            <AuditItem key={`${e.created_at}-${i}`} entry={e} />
          ))}
        </ul>
      </AdminSection>
    </>
  );
}
