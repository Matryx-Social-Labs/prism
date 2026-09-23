"use client";

/**
 * Every labelling batch with its progress, and the switches on it: list a work
 * batch on the labeller dashboard (which also closes anonymous joining), open
 * or close it, fill in the languages its tasks need; review and publish a
 * practice round or a test. Counts only — never what anyone answered.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AdminSection, AdminTitle, Quiet, TextButton, useAdmin } from "@/components/admin/AdminShell";
import { fetchBatches, gateLanguages, istTime, setListed, setOpen, type AdminBatch } from "@/lib/admin";
import { KIND_QUESTION } from "@/lib/labeller";

const PURPOSE_TITLE: Record<AdminBatch["purpose"], string> = {
  work: "Work",
  practice: "Practice rounds",
  qualify: "Tests",
};

export default function BatchesPage() {
  const { session } = useAdmin();
  const [batches, setBatches] = useState<AdminBatch[] | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    try {
      setBatches((await fetchBatches(session)).batches);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load batches");
    }
  }, [session]);

  useEffect(() => {
    void load();
  }, [load]);

  const act = async (change: () => Promise<unknown>) => {
    setError("");
    setNote("");
    try {
      await change();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That change was refused");
    }
    await load();
  };

  const gate = (key: string) =>
    act(async () => {
      const { gated } = await gateLanguages(session, key);
      setNote(`Gated: ${Object.entries(gated).map(([k, v]) => `${k} ${v}`).join(", ")}`);
    });

  return (
    <>
      <AdminTitle>Batches</AdminTitle>
      {error && (
        <p role="alert" className="mt-5 text-[14px]" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}
      {note && (
        <p aria-live="polite" className="mt-5 font-mono text-[12px]" style={{ color: "var(--ink-2)" }}>
          {note}
        </p>
      )}
      {(["work", "practice", "qualify"] as const).map((purpose) => {
        const rows = batches?.filter((b) => b.purpose === purpose) ?? [];
        return (
          <AdminSection key={purpose} title={`${PURPOSE_TITLE[purpose]} · ${rows.length}`}>
            {batches && rows.length === 0 && <Quiet>None yet.</Quiet>}
            <ul>
              {rows.map((b) => (
                <li key={b.key} className="border-t py-3" style={{ borderColor: "var(--line)" }}>
                  <p className="text-[15px] font-semibold">{b.name}</p>
                  <p className="mt-0.5 text-[14px]" style={{ color: "var(--ink-2)" }}>
                    {KIND_QUESTION[b.kind] ?? b.kind} · {b.open ? "Open" : "Closed"}
                    {b.listed && " · On the labeller dashboard"}
                    {b.self_join && " · Anyone with the link can join"}
                  </p>
                  <p className="mt-0.5 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
                    {b.key} · {b.answered_tasks} OF {b.tasks} ANSWERED · {b.responses} ANSWERS · {b.people} PEOPLE ·{" "}
                    {b.gated} OF {b.tasks} LANGUAGE-GATED · {istTime(b.created_at)}
                  </p>
                  <div className="mt-1 flex flex-wrap gap-x-4">
                    {purpose === "work" ? (
                      <>
                        <TextButton onClick={() => void act(() => setListed(session, b.key, !b.listed))} muted={b.listed}>
                          {b.listed ? "Take off the dashboard" : "List on the dashboard"}
                        </TextButton>
                        <TextButton onClick={() => void act(() => setOpen(session, b.key, !b.open))} muted={b.open}>
                          {b.open ? "Close" : "Open"}
                        </TextButton>
                        {b.gated < b.tasks && <TextButton onClick={() => void gate(b.key)}>Fill in languages</TextButton>}
                      </>
                    ) : (
                      <>
                        <Link
                          href={`/admin/batches/${encodeURIComponent(b.key)}`}
                          className="inline-flex min-h-[44px] items-center text-[14px] font-semibold underline-offset-4 hover:underline"
                          style={{ color: "var(--accent)" }}
                        >
                          Review{b.open ? "" : " and publish"}
                        </Link>
                        {b.open && (
                          <TextButton onClick={() => void act(() => setOpen(session, b.key, false))} muted>
                            Unpublish
                          </TextButton>
                        )}
                      </>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </AdminSection>
        );
      })}
    </>
  );
}
