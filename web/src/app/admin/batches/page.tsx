"use client";

/**
 * Every labelling batch with its progress, and the switches on it: list a work
 * batch on the labeller dashboard (which also closes anonymous joining), open
 * or close it, fill in the languages its tasks need; review and publish a
 * practice round or a test. Counts only — never what anyone answered.
 *
 * A progress board (admin charts, phase 4): each batch a panel with how many
 * of its tasks are answered and, for work, how many carry a language gate;
 * search by name or key, and filter by state.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AdminSection, AdminTitle, Quiet, TextButton, useAdmin } from "@/components/admin/AdminShell";
import { Badge, FilterSeg, Progress, SearchBox, matches } from "@/components/admin/ui";
import { fetchBatches, gateLanguages, istTime, setListed, setOpen, type AdminBatch } from "@/lib/admin";
import { KIND_QUESTION } from "@/lib/labeller";

const PURPOSE_TITLE: Record<AdminBatch["purpose"], string> = {
  work: "Work",
  practice: "Practice rounds",
  qualify: "Tests",
};

type Show = "all" | "open" | "closed" | "listed";
const SHOWN: Record<Show, (b: AdminBatch) => boolean> = {
  all: () => true,
  open: (b) => b.open,
  closed: (b) => !b.open,
  listed: (b) => b.listed,
};

export default function BatchesPage() {
  const { session } = useAdmin();
  const [batches, setBatches] = useState<AdminBatch[] | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [query, setQuery] = useState("");
  const [show, setShow] = useState<Show>("all");

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
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <SearchBox label="Search batches by name or key" value={query} onChange={setQuery} />
        <FilterSeg
          label="Show"
          value={show}
          onChange={setShow}
          options={(["all", "open", "closed", "listed"] as const).map((v) => ({
            value: v,
            label: v === "all" ? "All" : v === "listed" ? "On the dashboard" : v[0].toUpperCase() + v.slice(1),
            count: batches?.filter(SHOWN[v]).length ?? 0,
          }))}
        />
      </div>
      {(["work", "practice", "qualify"] as const).map((purpose) => {
        const all = batches?.filter((b) => b.purpose === purpose) ?? [];
        const rows = all.filter((b) => SHOWN[show](b) && matches(query, b.name, b.key));
        return (
          <AdminSection key={purpose} title={rows.length < all.length ? `${PURPOSE_TITLE[purpose]} · ${rows.length} of ${all.length}` : `${PURPOSE_TITLE[purpose]} · ${all.length}`}>
            {batches && all.length === 0 && <Quiet>None yet.</Quiet>}
            {all.length > 0 && rows.length === 0 && <Quiet>None match.</Quiet>}
            <ul className="grid gap-3 lg:grid-cols-2">
              {rows.map((b) => (
                <li key={b.key} className="admin-panel">
                  <p className="text-[15px] font-semibold">{b.name}</p>
                  <p className="mt-0.5 text-[14px]" style={{ color: "var(--ink-2)" }}>
                    {KIND_QUESTION[b.kind] ?? b.kind}
                  </p>
                  <p className="mt-2 flex flex-wrap gap-1.5">
                    <Badge strong={b.open}>{b.open ? "Open" : "Closed"}</Badge>
                    {b.listed && <Badge>On the labeller dashboard</Badge>}
                    {/* api/routes/label.join refuses a listed batch and any round,
                        whatever self_join says: only say what is true. */}
                    {b.self_join && !b.listed && b.purpose === "work" && <Badge>Anyone with the link can join</Badge>}
                  </p>
                  <div className="mt-3 space-y-2.5">
                    <Progress label="Tasks answered" done={b.answered_tasks} total={b.tasks} />
                    {purpose === "work" && <Progress label="Tasks with a language gate" done={b.gated} total={b.tasks} />}
                  </div>
                  <p className="mt-2.5 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
                    {b.key} · {b.responses} ANSWERS · {b.people} PEOPLE · {istTime(b.created_at)}
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
