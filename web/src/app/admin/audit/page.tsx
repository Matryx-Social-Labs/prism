"use client";

// Every change made from /admin, newest first, with the founder who made it
// (common/admin_audit). Read-only: the app never edits or deletes these rows.

import { useEffect, useState } from "react";

import { AdminSection, AdminTitle, useAdmin } from "@/components/admin/AdminShell";
import { fetchAudit, istTime, type AuditEntry } from "@/lib/admin";

export default function AuditPage() {
  const { session } = useAdmin();
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAudit(session)
      .then((r) => setEntries(r.entries))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load the audit log"));
  }, [session]);

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
        <ul>
          {entries?.map((e, i) => (
            <li key={`${e.created_at}-${i}`} className="border-t py-3" style={{ borderColor: "var(--line)" }}>
              <p className="text-[15px]">
                <span className="font-semibold">{e.action}</span> · {e.target}
              </p>
              <p className="mt-0.5 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
                {istTime(e.created_at)} IST · {e.actor}
              </p>
            </li>
          ))}
        </ul>
      </AdminSection>
    </>
  );
}
