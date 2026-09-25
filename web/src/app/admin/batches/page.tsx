"use client";

/**
 * Every labelling batch with its progress, and the switches on it: list a work
 * batch on the labeller dashboard (which also closes anonymous joining), open
 * or close it, fill in the languages its tasks need; review and publish a
 * practice round or a test. Counts only — never what anyone answered.
 *
 * A progress board (Design System v2 · Batches): each batch a row with how
 * many of its tasks are answered and, for work, how many carry a language
 * gate, as KofNBars; search by name or key, and filter by state.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AdminSection, AdminTitle, Quiet, useAdmin } from "@/components/admin/AdminShell";
import { istClock } from "@/components/admin/AuditItem";
import { dayLabel } from "@/components/admin/charts/format";
import { Act, Badge, FilterSwitch, KofNBar, SearchBox, matches } from "@/components/admin/ui";
import { Alert } from "@/components/ui";
import { fetchBatches, gateLanguages, setListed, setOpen, type AdminBatch } from "@/lib/admin";
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
const SHOW_WORD: Record<Show, string> = { all: "All", open: "Open", closed: "Closed", listed: "On the dashboard" };

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
      setNote(`Gated ${key}: ${Object.entries(gated).map(([k, v]) => `${k} ${v}`).join(" · ") || "nothing new"}`);
    });

  return (
    <>
      <AdminTitle>Batches</AdminTitle>
      {error && <Alert tone="error">{error}</Alert>}
      {note && (
        <p aria-live="polite" className="font-mono text-[12px] [overflow-wrap:anywhere]" style={{ color: "var(--ink-2)" }}>
          {note}
        </p>
      )}
      <div className="flex flex-wrap items-end gap-2.5">
        <SearchBox placeholder="Name or key" value={query} onChange={setQuery} />
        <FilterSwitch
          label="Show"
          value={show}
          onChange={setShow}
          options={(["all", "open", "closed", "listed"] as const).map((v) => ({ value: v, label: SHOW_WORD[v], count: batches?.filter(SHOWN[v]).length ?? 0 }))}
        />
      </div>
      {(["work", "practice", "qualify"] as const).map((purpose) => {
        const all = batches?.filter((b) => b.purpose === purpose) ?? [];
        const rows = all.filter((b) => SHOWN[show](b) && matches(query, b.name, b.key));
        const n = all.length;
        return (
          <AdminSection
            key={purpose}
            title={rows.length < n ? `${PURPOSE_TITLE[purpose]} · ${rows.length} of ${n}` : PURPOSE_TITLE[purpose]}
            sub={batches ? `${n} ${n === 1 ? "BATCH" : "BATCHES"}` : undefined}
          >
            {batches && n === 0 && <Quiet>None yet.</Quiet>}
            {n > 0 && rows.length === 0 && <Quiet>None match.</Quiet>}
            <ul>
              {rows.map((b) => (
                <BatchRow key={b.key} b={b} act={act} gate={gate} />
              ))}
            </ul>
          </AdminSection>
        );
      })}
    </>
  );
}

function BatchRow({ b, act, gate }: { b: AdminBatch; act: (change: () => Promise<unknown>) => Promise<void>; gate: (key: string) => Promise<void> }) {
  const { session } = useAdmin();
  const work = b.purpose === "work";
  return (
    <li className="grid gap-2.5 border-b py-3.5" style={{ borderColor: "var(--line)" }}>
      <div className="flex flex-wrap items-center gap-2">
        <b className="min-w-0 flex-[1_1_200px] [overflow-wrap:anywhere]" style={{ font: "var(--t-title-s)" }}>
          {b.name}
        </b>
        {/* A round is open exactly when it is published: one word for it. */}
        {work ? <Badge tone={b.open ? "ink" : "dashed"}>{b.open ? "OPEN" : "CLOSED"}</Badge> : <Badge tone={b.open ? "ink" : "dashed"}>{b.open ? "PUBLISHED" : "NOT PUBLISHED"}</Badge>}
        {b.listed && <Badge>On the labeller dashboard</Badge>}
        {/* api/routes/label.join refuses a listed batch and any round,
            whatever self_join says: only say what is true. */}
        {b.self_join && !b.listed && work && <Badge>Anyone with the link can join</Badge>}
      </div>
      <p className="text-[14px]" style={{ color: "var(--ink-2)" }}>
        {KIND_QUESTION[b.kind] ?? b.kind}
      </p>
      <div className="grid gap-2.5 lg:grid-cols-2">
        <KofNBar label="Tasks answered" k={b.answered_tasks} n={b.tasks} />
        {work && <KofNBar label="Tasks with a language gate" k={b.gated} n={b.tasks} />}
      </div>
      <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
        <span className="min-w-0 flex-[1_1_240px] font-mono text-[11.5px] [overflow-wrap:anywhere]" style={{ color: "var(--ink-3)" }}>
          {b.key} · {b.responses.toLocaleString("en-IN")} ANSWERS · {b.people} {b.people === 1 ? "PERSON" : "PEOPLE"} · CREATED{" "}
          {`${dayLabel(b.created_at)} ${istClock(b.created_at)}`.toUpperCase()} IST
        </span>
        {work ? (
          <span className="flex flex-wrap gap-1.5">
            <Act onClick={() => void act(() => setListed(session, b.key, !b.listed))}>{b.listed ? "Take off the dashboard" : "List on the dashboard"}</Act>
            <Act onClick={() => void act(() => setOpen(session, b.key, !b.open))}>{b.open ? "Close" : "Open"}</Act>
            {b.gated < b.tasks && (
              <Act variant="secondary" onClick={() => void gate(b.key)}>
                Fill in languages
              </Act>
            )}
          </span>
        ) : (
          <span className="flex flex-wrap gap-1.5">
            {b.open && <Act onClick={() => void act(() => setOpen(session, b.key, false))}>Unpublish</Act>}
            <Link href={`/admin/batches/${encodeURIComponent(b.key)}`} className={`p-btn p-btn--sm p-hit ${b.open ? "p-btn--ghost" : "p-btn--secondary"}`}>
              {b.open ? "Review" : "Review and publish"}
            </Link>
          </span>
        )}
      </div>
    </li>
  );
}
