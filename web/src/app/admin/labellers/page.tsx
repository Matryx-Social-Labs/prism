"use client";

/**
 * Who applied, who labels, and where each one stands per kind — and the
 * changes a founder makes to them: approve, pause, remove, add an account
 * directly, grant or withdraw a kind. Every change goes through
 * common/label_ops (the same code tools/label_admin runs) and lands in the
 * audit log with the founder's email.
 *
 * Removing someone keeps their answers (they are the measurement) and takes
 * every kind away (founder decision D5, 2026-09-23).
 */

import { useCallback, useEffect, useState } from "react";

import { AdminSection, AdminTitle, Quiet, TextButton, useAdmin } from "@/components/admin/AdminShell";
import {
  addLabeller,
  fetchLabellers,
  istTime,
  setLabellerStatus,
  setQualification,
  type AdminLabeller,
  type Standing,
} from "@/lib/admin";
import { KIND_QUESTION } from "@/lib/labeller";
import { langName } from "@/lib/languages";

type Data = { labellers: AdminLabeller[]; board: Standing[]; languages: string[] };

const STATUS_WORD: Record<AdminLabeller["status"], string> = {
  applied: "Applied",
  active: "Active",
  paused: "Paused",
  removed: "Removed",
};

export default function LabellersPage() {
  const { session } = useAdmin();
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setData(await fetchLabellers(session));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load labellers");
    }
  }, [session]);

  useEffect(() => {
    void load();
  }, [load]);

  // Every change: run it, then re-read, so the page never shows a state the
  // server did not accept.
  const act = async (change: () => Promise<unknown>) => {
    setError("");
    try {
      await change();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That change was refused");
    }
    await load();
  };

  const status = (l: AdminLabeller, to: "active" | "paused" | "removed") => {
    if (to === "removed" && !window.confirm(`Remove ${l.email}? Their answers stay; every kind they passed is withdrawn.`)) return;
    void act(() => setLabellerStatus(session, l.email, to));
  };

  const applicants = data?.labellers.filter((l) => l.status === "applied") ?? [];
  const others = data?.labellers.filter((l) => l.status !== "applied") ?? [];

  return (
    <>
      <AdminTitle>Labellers</AdminTitle>
      {error && (
        <p role="alert" className="mt-5 text-[14px]" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}

      <AdminSection title={`Waiting for approval · ${applicants.length}`}>
        {data && applicants.length === 0 && <Quiet>No applications waiting.</Quiet>}
        <ul>
          {applicants.map((l) => (
            <PersonRow key={l.email} l={l}>
              <TextButton onClick={() => void act(() => setLabellerStatus(session, l.email, "active"))}>Approve</TextButton>
              <TextButton onClick={() => status(l, "removed")} muted>
                Decline
              </TextButton>
            </PersonRow>
          ))}
        </ul>
      </AdminSection>

      <AdminSection title={`Labellers · ${others.length}`}>
        {data && others.length === 0 && <Quiet>Nobody approved yet.</Quiet>}
        <ul>
          {others.map((l) => (
            <PersonRow key={l.email} l={l}>
              {l.status === "active" && <TextButton onClick={() => status(l, "paused")}>Pause</TextButton>}
              {l.status !== "active" && <TextButton onClick={() => status(l, "active")}>{l.status === "paused" ? "Resume" : "Restore"}</TextButton>}
              {l.status !== "removed" && (
                <TextButton onClick={() => status(l, "removed")} muted>
                  Remove
                </TextButton>
              )}
            </PersonRow>
          ))}
        </ul>
      </AdminSection>

      <AdminSection title="Standing per kind">
        {data && data.board.length === 0 && <Quiet>Nobody has passed or been granted a kind yet.</Quiet>}
        <ul>
          {data?.board.map((b) => (
            <li key={`${b.email}-${b.kind}`} className="border-t py-3" style={{ borderColor: "var(--line)" }}>
              <p className="text-[15px]">
                <span className="font-semibold">{b.email}</span> · {KIND_QUESTION[b.kind] ?? b.kind}
              </p>
              <p className="mt-0.5 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
                {b.passed ? (b.granted_by ? `GRANTED BY ${b.granted_by}` : "PASSED") : "NOT PASSED"}
                {b.best_score !== null && ` · BEST ${Math.round(b.best_score * 100)}%`} · {b.attempts} ATTEMPTS ·{" "}
                {b.checks_total ? `CHECKS ${b.checks_right}/${b.checks_total}` : "NO CHECKS YET"}
              </p>
              <div className="mt-1.5">
                <TextButton onClick={() => void act(() => setQualification(session, b.email, b.kind, !b.passed))} muted={b.passed}>
                  {b.passed ? "Withdraw" : "Grant"}
                </TextButton>
              </div>
            </li>
          ))}
        </ul>
      </AdminSection>

      {data && (
        <GrantForm
          emails={data.labellers.filter((l) => l.status === "active").map((l) => l.email)}
          onGrant={(email, kind) => act(() => setQualification(session, email, kind, true))}
        />
      )}
      {data && <AddForm languages={data.languages} onAdd={(email, langs) => act(() => addLabeller(session, email, langs))} />}
    </>
  );
}

function PersonRow({ l, children }: { l: AdminLabeller; children: React.ReactNode }) {
  return (
    <li className="border-t py-3" style={{ borderColor: "var(--line)" }}>
      <p className="text-[15px]">
        <span className="font-semibold">{l.email}</span>
        {l.name && <span style={{ color: "var(--ink-2)" }}> · {l.name}</span>}
      </p>
      <p className="mt-0.5 text-[14px]" style={{ color: "var(--ink-2)" }}>
        {STATUS_WORD[l.status]} · reads {l.languages_read.map(langName).join(", ") || "nothing yet"}
      </p>
      {l.note && (
        <p className="mt-1 text-[14px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
          “{l.note}”
        </p>
      )}
      <p className="mt-0.5 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
        APPLIED {istTime(l.created_at)} · {l.answers} ANSWERS
        {l.last_answer_at && ` · LAST ${istTime(l.last_answer_at)}`}
        {l.approved_by && ` · APPROVED BY ${l.approved_by}`}
      </p>
      <div className="mt-1.5 flex flex-wrap gap-x-4">{children}</div>
    </li>
  );
}

function GrantForm({ emails, onGrant }: { emails: string[]; onGrant: (email: string, kind: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [kind, setKind] = useState(Object.keys(KIND_QUESTION)[0]);
  if (emails.length === 0) return null;
  return (
    <AdminSection title="Qualify without a test">
      <p className="mb-3 text-[14px]" style={{ color: "var(--ink-2)" }}>
        For a kind with no test yet, or someone whose judgement you already trust. Recorded as a grant, never as a score.
      </p>
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={async (e) => {
          e.preventDefault();
          if (email) await onGrant(email, kind);
        }}
      >
        <label className="text-[14px]">
          <span className="block font-semibold">Labeller</span>
          <select className="mt-1 h-[44px] rounded-[8px] border px-2 text-[16px]" style={{ borderColor: "var(--line-strong)", background: "var(--surface)" }} value={email} onChange={(e) => setEmail(e.target.value)}>
            <option value="">Choose…</option>
            {emails.map((x) => (
              <option key={x} value={x}>
                {x}
              </option>
            ))}
          </select>
        </label>
        <label className="text-[14px]">
          <span className="block font-semibold">Kind</span>
          <select className="mt-1 h-[44px] rounded-[8px] border px-2 text-[16px]" style={{ borderColor: "var(--line-strong)", background: "var(--surface)" }} value={kind} onChange={(e) => setKind(e.target.value)}>
            {Object.entries(KIND_QUESTION).map(([k, q]) => (
              <option key={k} value={k}>
                {q}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="btn btn-secondary" disabled={!email}>
          Grant
        </button>
      </form>
    </AdminSection>
  );
}

function AddForm({ languages, onAdd }: { languages: string[]; onAdd: (email: string, langs: string[]) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [chosen, setChosen] = useState<string[]>(["en"]);
  const toggle = (code: string) => setChosen((c) => (c.includes(code) ? c.filter((x) => x !== code) : [...c, code]));
  return (
    <AdminSection title="Add a labeller">
      <p className="mb-3 text-[14px]" style={{ color: "var(--ink-2)" }}>
        They need a Prism account first. Added people are active at once, without applying.
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          await onAdd(email.trim(), chosen);
          setEmail("");
        }}
      >
        <label className="block text-[14px]">
          <span className="font-semibold">Their account email</span>
          <input
            type="email"
            required
            className="mt-1 block h-[44px] w-full max-w-[420px] rounded-[8px] border px-3 text-[16px]"
            style={{ borderColor: "var(--line-strong)", background: "var(--surface)" }}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <fieldset className="mt-4">
          <legend className="text-[14px] font-semibold">They read</legend>
          <div className="mt-2 grid grid-cols-2 gap-x-6 sm:grid-cols-4">
            {languages.map((code) => (
              <label key={code} className="flex min-h-[44px] items-center gap-2.5 text-[15px]">
                <input type="checkbox" checked={chosen.includes(code)} onChange={() => toggle(code)} />
                {langName(code)}
              </label>
            ))}
          </div>
        </fieldset>
        <button type="submit" className="btn btn-primary mt-4" disabled={!email || chosen.length === 0}>
          Add labeller
        </button>
      </form>
    </AdminSection>
  );
}
