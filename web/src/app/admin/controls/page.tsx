"use client";

/**
 * The switches, read-only, and the one control: ask the worker to collect now.
 * Founder decision D4 (2026-09-23): flags are shown, never set, from here —
 * setting them would move them out of the environment and change how a bad
 * change is rolled back. The values are this API's own view; the worker reads
 * its own environment, which is how a feature runs in shadow there first.
 */

import { useEffect, useState } from "react";

import { AdminSection, AdminTitle, useAdmin } from "@/components/admin/AdminShell";
import { fetchFlags, triggerCollection, type Flag } from "@/lib/admin";

export default function ControlsPage() {
  const { session } = useAdmin();
  const [flags, setFlags] = useState<Flag[] | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchFlags(session)
      .then((r) => setFlags(r.flags))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load the switches"));
  }, [session]);

  const collecting = flags?.find((f) => f.name === "PRISM_INGESTION_ENABLED")?.value;

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
    <>
      <AdminTitle>Controls</AdminTitle>
      {error && (
        <p role="alert" className="mt-5 text-[14px]" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}

      <AdminSection title="Collect now">
        <p className="text-[15px]" style={{ color: "var(--ink-2)" }}>
          Collection runs on its own schedule. This asks the worker to run it once now.
        </p>
        <button type="button" className="btn btn-primary mt-4" disabled={sending || collecting === undefined} onClick={() => void collect()}>
          Collect now
        </button>
        {note && (
          <p aria-live="polite" className="mt-3 text-[14px]" style={{ color: "var(--ink-2)" }}>
            {note}
          </p>
        )}
      </AdminSection>

      <AdminSection title="Switches">
        <p className="mb-3 text-[14px]" style={{ color: "var(--ink-2)" }}>
          As the API sees them. They are changed in Railway&apos;s environment, not here; the worker has its own copy.
        </p>
        <ul>
          {flags?.map((f) => (
            <li key={f.name} className="flex items-baseline justify-between gap-4 border-t py-2.5" style={{ borderColor: "var(--line)" }}>
              <span>
                <span className="block text-[15px]" style={{ color: "var(--ink)" }}>{f.does}</span>
                <span className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>{f.name}</span>
              </span>
              <span className="font-mono text-[14px] tabular-nums" style={{ color: "var(--ink)" }}>
                {typeof f.value === "boolean" ? (f.value ? "ON" : "OFF") : f.value}
              </span>
            </li>
          ))}
        </ul>
      </AdminSection>
    </>
  );
}
