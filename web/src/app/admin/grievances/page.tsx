"use client";

/**
 * The complaint queue (api/routes/grievances.py; IT Rules Part III). Every
 * complaint filed at /grievance, newest first, open ones shown first: what it
 * is about, who sent it, the page, the words, and the day it must be decided
 * by (15 days). A founder resolves or rejects it once, with the outcome in the
 * words the complainant will read — asked in place before it is done, because
 * it is emailed to them, counted in the public monthly report and recorded in
 * the audit log. A complaint whose acknowledgement email failed says so: it
 * must be acknowledged by hand within 24 hours.
 */

import { useCallback, useEffect, useState } from "react";

import { AdminHead, Quiet, useAdmin } from "@/components/admin/AdminShell";
import { istClock } from "@/components/admin/AuditItem";
import { dayLabel } from "@/components/admin/charts/format";
import { Act, Badge, Confirm, FilterSwitch } from "@/components/admin/ui";
import { Alert, TextField } from "@/components/ui";
import { decideGrievance, fetchGrievances, type AdminGrievance, type GrievanceStatus } from "@/lib/admin";

type Decided = Exclude<GrievanceStatus, "open">;
type Show = GrievanceStatus | "all";
const WORD: Record<GrievanceStatus, string> = { open: "Open", resolved: "Resolved", rejected: "Rejected" };
const OUTCOME_MIN = 10;

/** "24 SEPT 09:12 IST": an IST day and time, for a mono line. */
const stamp = (iso: string) => `${dayLabel(iso)} ${istClock(iso)} IST`.toUpperCase();

export default function GrievancesPage() {
  const { session } = useAdmin();
  const [list, setList] = useState<AdminGrievance[] | null>(null);
  const [error, setError] = useState("");
  const [told, setTold] = useState("");
  const [show, setShow] = useState<Show>("open");

  const load = useCallback(async () => {
    try {
      setList((await fetchGrievances(session)).grievances);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the complaints");
    }
  }, [session]);

  useEffect(() => {
    void load();
  }, [load]);

  // Run it, say whether the complainant was told, then re-read.
  const decide = async (g: AdminGrievance, status: Decided, outcome: string) => {
    setError("");
    setTold("");
    try {
      const r = await decideGrievance(session, g.ref, status, outcome);
      const done = `${g.ref} is ${WORD[status].toLowerCase()}`;
      setTold(r.emailed ? `${done}, and the outcome was emailed to ${g.email}.` : `${done}, but the outcome could not be emailed. Write to ${g.email} yourself.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "That decision was refused");
    }
    await load();
  };

  const all = list ?? [];
  const shown = all.filter((g) => show === "all" || g.status === show);
  const open = all.filter((g) => g.status === "open").length;

  return (
    <>
      <AdminHead title="Grievances" line={list ? `${open} OPEN · EACH DECIDED WITHIN 15 DAYS` : null} />
      {error && <Alert tone="error">{error}</Alert>}
      {told && <Alert>{told}</Alert>}
      {all.length > 0 && (
        <FilterSwitch
          label="Status"
          value={show}
          onChange={setShow}
          options={(["open", "resolved", "rejected", "all"] as const).map((v) => ({
            value: v,
            label: v === "all" ? "All" : WORD[v],
            count: v === "all" ? all.length : all.filter((g) => g.status === v).length,
          }))}
        />
      )}
      {list && all.length === 0 && <Quiet>No complaints yet. Each one filed at /grievance appears here with the day it must be decided by.</Quiet>}
      {all.length > 0 && shown.length === 0 && <Quiet>Nothing {WORD[show as GrievanceStatus]?.toLowerCase() ?? "here"}.</Quiet>}
      <ul>
        {shown.map((g) => (
          <GrievanceRow key={g.ref} g={g} onDecide={(status, outcome) => decide(g, status, outcome)} />
        ))}
      </ul>
    </>
  );
}

function GrievanceRow({ g, onDecide }: { g: AdminGrievance; onDecide: (status: Decided, outcome: string) => Promise<void> }) {
  const [outcome, setOutcome] = useState("");
  const [asking, setAsking] = useState<Decided | null>(null);
  const [busy, setBusy] = useState(false);
  const overdue = g.status === "open" && Date.parse(g.decide_by) < Date.now();
  const ready = outcome.trim().length >= OUTCOME_MIN;

  const confirm = async () => {
    if (!asking) return;
    setBusy(true);
    await onDecide(asking, outcome.trim());
    setBusy(false);
    setAsking(null);
  };

  return (
    <li className="grid gap-2 border-b py-4" style={{ borderColor: "var(--line)" }} aria-label={g.ref}>
      <p className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[12px]" style={{ color: "var(--ink-2)" }}>{g.ref}</span>
        <Badge tone={g.status === "open" ? "dashed" : "ink"}>{WORD[g.status].toUpperCase()}</Badge>
        {overdue && <Badge tone="outline">OVERDUE</Badge>}
        {!g.acknowledged_at && <Badge tone="dashed">NOT ACKNOWLEDGED BY EMAIL</Badge>}
      </p>
      <p className="text-[15px] font-semibold leading-[1.35]">{g.category}</p>
      <p className="font-mono text-[11.5px] [overflow-wrap:anywhere]" style={{ color: "var(--ink-3)" }}>
        RECEIVED {stamp(g.created_at)} · {g.resolved_at ? `DECIDED ${stamp(g.resolved_at)}` : `DECIDE BY ${stamp(g.decide_by)}`}
      </p>
      <p className="text-[14px] [overflow-wrap:anywhere]">
        {g.name && <b className="mr-2 font-semibold">{g.name}</b>}
        <a href={`mailto:${g.email}?subject=${encodeURIComponent(`Your complaint · ${g.ref}`)}`} className="p-link font-mono text-[12.5px]">{g.email}</a>
      </p>
      {g.subject_url && (
        <a href={g.subject_url} className="p-link justify-self-start text-[14px] [overflow-wrap:anywhere]">{g.subject_url}</a>
      )}
      <p className="max-w-[72ch] whitespace-pre-wrap text-[14.5px] leading-[1.55] [overflow-wrap:anywhere]" style={{ color: "var(--ink)" }}>{g.body}</p>

      {g.status !== "open" ? (
        <p className="max-w-[72ch] whitespace-pre-wrap text-[14px] leading-[1.5]" style={{ color: "var(--ink-2)" }}>
          <span className="p-eyebrow mr-2">Outcome</span>
          {g.outcome}
        </p>
      ) : (
        <div className="grid max-w-[640px] gap-2">
          <TextField
            label="Outcome, as the complainant will read it"
            hint={`What was decided and what was done. At least ${OUTCOME_MIN} characters; emailed to them and not editable after.`}
            multiline
            rows={3}
            maxLength={5000}
            value={outcome}
            onChange={setOutcome}
          />
          {asking ? (
            <Confirm yes={asking === "resolved" ? "Yes, resolve" : "Yes, reject"} danger={asking === "rejected"} busy={busy} onYes={() => void confirm()} onNo={() => setAsking(null)}>
              {`${asking === "resolved" ? "Resolve" : "Reject"} ${g.ref}? The outcome is emailed to ${g.email} and counted in the public report.`}
            </Confirm>
          ) : (
            <div className="flex gap-1.5">
              <Act variant="secondary" disabled={!ready} onClick={() => setAsking("resolved")}>Resolve</Act>
              <Act disabled={!ready} onClick={() => setAsking("rejected")}>Reject</Act>
            </div>
          )}
        </div>
      )}
    </li>
  );
}
