"use client";

/**
 * Who applied, who labels, and where each one stands per kind — and the
 * changes a founder makes to them: approve, pause, remove, add an account
 * directly, grant or withdraw a kind. Every change goes through
 * common/label_ops (the same code tools/label_admin runs) and lands in the
 * audit log with the founder's email.
 *
 * Removing someone keeps their answers (they are the measurement) and takes
 * every kind away (founder decision D5, 2026-09-23); it is asked in place,
 * under the row, before it is done.
 *
 * Standing is drawn per labeller: each kind they hold or tried, with hidden
 * checks right as a KofNBar — a count, since ten checks are not a rate.
 */

import { useCallback, useEffect, useState } from "react";

import { AdminSection, AdminTitle, Quiet, useAdmin } from "@/components/admin/AdminShell";
import { istClock } from "@/components/admin/AuditItem";
import { dayLabel } from "@/components/admin/charts/format";
import { Act, Badge, Confirm, FilterSwitch, KofNBar, SearchBox, matches } from "@/components/admin/ui";
import { Alert, SelectField, TextField } from "@/components/ui";
import { addLabeller, fetchLabellers, setLabellerStatus, setQualification, type AdminLabeller, type Standing } from "@/lib/admin";
import { KIND_QUESTION } from "@/lib/labeller";
import { langName, langNative } from "@/lib/languages";

type Data = { labellers: AdminLabeller[]; board: Standing[]; languages: string[] };
type Show = "all" | Exclude<AdminLabeller["status"], "applied">;

const STATUS_WORD: Record<AdminLabeller["status"], string> = { applied: "Applied", active: "Active", paused: "Paused", removed: "Removed" };

/** "24 SEPT 09:12 IST": an IST day and time, for a mono line. */
const stamp = (iso: string) => `${dayLabel(iso)} ${istClock(iso)} IST`.toUpperCase();
/** A language in its own script; English by its name (its "native" label is the code EN). */
const own = (code: string) => (code === "en" ? langName(code) : langNative(code));
const reads = (l: AdminLabeller) => l.languages_read.map(own).join(", ") || "No languages yet";
const answers = (n: number) => `${n.toLocaleString("en-IN")} ${n === 1 ? "ANSWER" : "ANSWERS"}`;

export default function LabellersPage() {
  const { session } = useAdmin();
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [show, setShow] = useState<Show>("all");
  // The removal being asked about, in place under its row.
  const [asking, setAsking] = useState<string | null>(null);

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
    setAsking(null);
    try {
      await change();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That change was refused");
    }
    await load();
  };
  const status = (l: AdminLabeller, to: "active" | "paused" | "removed") => void act(() => setLabellerStatus(session, l.email, to));

  const nameOf = (email: string) => data?.labellers.find((l) => l.email === email)?.name;
  const applicants = data?.labellers.filter((l) => l.status === "applied") ?? [];
  const others = data?.labellers.filter((l) => l.status !== "applied") ?? [];
  const shown = others.filter((l) => (show === "all" || l.status === show) && matches(query, l.email, l.name));
  // Standing grouped by person — anyone with a standing, an applicant who
  // took a test included — under the same search and filter as the list.
  const board = data?.board ?? [];
  const standing = [...new Set(board.map((b) => b.email))]
    .map((email) => ({ email, kinds: board.filter((b) => b.email === email) }))
    .filter(({ email, kinds }) => (show === "all" || kinds[0].status === show) && matches(query, email, nameOf(email)));

  const removal = (l: AdminLabeller) =>
    asking === l.email && (
      <Confirm yes={l.status === "applied" ? "Yes, decline" : "Yes, remove"} danger onYes={() => status(l, "removed")} onNo={() => setAsking(null)}>
        {`${l.status === "applied" ? "Decline" : "Remove"} ${l.name ?? l.email}? `}
        {l.answers > 0
          ? `Their ${l.answers.toLocaleString("en-IN")} answers are kept, and every kind they qualified for is withdrawn.`
          : "Every kind they qualified for is withdrawn."}
      </Confirm>
    );

  return (
    <>
      <AdminTitle>Labellers</AdminTitle>
      {error && <Alert tone="error">{error}</Alert>}

      <AdminSection title="Waiting for approval" sub={data ? `${applicants.length} ${applicants.length === 1 ? "APPLICATION" : "APPLICATIONS"}` : undefined}>
        {data && applicants.length === 0 && <Quiet>No applications waiting.</Quiet>}
        <ul>
          {applicants.map((l) => (
            <li key={l.email} className="grid gap-2 border-b py-3" style={{ borderColor: "var(--line)" }}>
              <div className="grid items-center gap-x-4 gap-y-1.5 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1.4fr)_auto]">
                <Who l={l} />
                <div className="min-w-0 text-[14px]">
                  {reads(l)}
                  <span className="block font-mono text-[11.5px] [overflow-wrap:anywhere]" style={{ color: "var(--ink-3)" }}>
                    APPLIED {stamp(l.created_at)} · {answers(l.answers)}
                  </span>
                </div>
                <p className={`min-w-0 text-[14px] leading-[1.5] [overflow-wrap:anywhere] ${l.note ? "" : "max-lg:hidden"}`} style={{ color: "var(--ink-2)" }}>
                  {l.note ? `“${l.note}”` : "—"}
                </p>
                <div className="flex gap-1.5">
                  <Act variant="secondary" onClick={() => status(l, "active")}>
                    Approve
                  </Act>
                  <Act onClick={() => setAsking(l.email)}>Decline</Act>
                </div>
              </div>
              {removal(l)}
            </li>
          ))}
        </ul>
      </AdminSection>

      <AdminSection title={shown.length < others.length ? `Labellers · ${shown.length} of ${others.length}` : `Labellers · ${others.length}`}>
        {others.length > 0 && (
          <div className="flex flex-wrap items-end gap-2.5">
            <SearchBox placeholder="Email or name" value={query} onChange={setQuery} />
            <FilterSwitch
              label="Status"
              value={show}
              onChange={setShow}
              options={(["all", "active", "paused", "removed"] as const).map((v) => ({
                value: v,
                label: v === "all" ? "All" : STATUS_WORD[v],
                count: v === "all" ? others.length : others.filter((l) => l.status === v).length,
              }))}
            />
          </div>
        )}
        {data && others.length === 0 && <Quiet>Nobody approved yet.</Quiet>}
        {others.length > 0 && shown.length === 0 && <Quiet>Nobody matches.</Quiet>}
        <ul>
          {shown.map((l) => (
            <li key={l.email} className="grid gap-2 border-b py-3" style={{ borderColor: "var(--line)" }}>
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1.5 lg:grid-cols-[minmax(0,1.2fr)_auto_minmax(0,1fr)_auto]">
                <Who l={l} />
                <Badge tone={l.status === "active" ? "ink" : "dashed"}>{STATUS_WORD[l.status].toUpperCase()}</Badge>
                <div className="col-span-full min-w-0 text-[14px] lg:col-span-1">
                  {reads(l)} ·{" "}
                  <span className="font-mono text-[11.5px]" style={{ color: "var(--ink-3)" }}>
                    {answers(l.answers)}
                    {l.last_answer_at && ` · LAST ${stamp(l.last_answer_at)}`}
                  </span>
                </div>
                <div className="col-span-full flex gap-1.5 lg:col-span-1">
                  {l.status === "active" && <Act onClick={() => status(l, "paused")}>Pause</Act>}
                  {l.status !== "active" && (
                    <Act variant="secondary" onClick={() => status(l, "active")}>
                      {l.status === "paused" ? "Resume" : "Restore"}
                    </Act>
                  )}
                  {l.status !== "removed" && <Act onClick={() => setAsking(l.email)}>Remove</Act>}
                </div>
              </div>
              {removal(l)}
            </li>
          ))}
        </ul>
      </AdminSection>

      <AdminSection
        title="Standing per kind"
        hint="Hidden checks are the last 20 answered inside work. Below 80% of them, once 10 are answered, the kind is withdrawn until its test is passed again."
      >
        {data && data.board.length === 0 && <Quiet>Nobody has passed or been granted a kind yet.</Quiet>}
        <ul className="grid gap-3 lg:grid-cols-2">
          {standing.map(({ email, kinds }) => (
            <li key={email} className="admin-panel grid content-start gap-2">
              <p className="flex flex-wrap items-baseline gap-x-2">
                <b className="text-[15px] font-semibold">{nameOf(email) ?? email}</b>
                {nameOf(email) && (
                  <span className="font-mono text-[11.5px] [overflow-wrap:anywhere]" style={{ color: "var(--ink-3)" }}>
                    {email}
                  </span>
                )}
              </p>
              <ul>
                {kinds.map((b) => (
                  <KindRow key={b.kind} b={b} onToggle={() => void act(() => setQualification(session, b.email, b.kind, !b.passed))} />
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </AdminSection>

      {data && (
        <div className="grid gap-4 lg:grid-cols-2">
          <GrantForm
            emails={data.labellers.filter((l) => l.status === "active").map((l) => ({ value: l.email, label: l.name ? `${l.name} · ${l.email}` : l.email }))}
            onGrant={(email, kind) => act(() => setQualification(session, email, kind, true))}
          />
          <AddForm languages={data.languages} onAdd={(email, langs) => act(() => addLabeller(session, email, langs))} />
        </div>
      )}
    </>
  );
}

function Who({ l }: { l: AdminLabeller }) {
  return (
    <div className="min-w-0">
      <b className="block text-[14.5px] font-semibold leading-[1.3] [overflow-wrap:anywhere]">{l.name ?? l.email}</b>
      {l.name && (
        <span className="block font-mono text-[11.5px] [overflow-wrap:anywhere]" style={{ color: "var(--ink-3)" }}>
          {l.email}
        </span>
      )}
    </div>
  );
}

/** One kind a labeller holds or tried: its state, the hidden checks, grant or withdraw. */
function KindRow({ b, onToggle }: { b: Standing; onToggle: () => void }) {
  const word = b.passed ? (b.granted_by ? "Granted" : "Passed") : "Not passed";
  return (
    <li
      className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 border-t py-2 sm:grid-cols-[minmax(0,1.1fr)_minmax(0,1.3fr)_auto]"
      style={{ borderColor: "var(--line)" }}
    >
      <div className="min-w-0">
        <p className="text-[13.5px] font-semibold leading-[1.3]">{KIND_QUESTION[b.kind] ?? b.kind}</p>
        <p className="mt-0.5 flex flex-wrap items-center gap-1.5">
          <Badge tone={word === "Passed" ? "ink" : word === "Granted" ? "outline" : "dashed"}>{word}</Badge>
          <span className="font-mono text-[11px] [overflow-wrap:anywhere]" style={{ color: "var(--ink-3)" }}>
            {b.granted_by ? `GRANTED BY ${b.granted_by}` : `${b.attempts} ${b.attempts === 1 ? "TRY" : "TRIES"}`}
          </span>
        </p>
      </div>
      <div className="order-last col-span-full min-w-0 sm:order-none sm:col-span-1">
        {b.checks_total ? (
          <KofNBar label="Hidden checks right" k={b.checks_right} n={b.checks_total} />
        ) : (
          <span className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
            NO CHECKS YET
          </span>
        )}
      </div>
      <Act onClick={onToggle}>{b.passed ? "Withdraw" : "Grant"}</Act>
    </li>
  );
}

function GrantForm({ emails, onGrant }: { emails: Array<{ value: string; label: string }>; onGrant: (email: string, kind: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [kind, setKind] = useState(Object.keys(KIND_QUESTION)[0]);
  return (
    <form
      className="admin-panel grid content-start gap-3"
      aria-labelledby="grant-form"
      onSubmit={async (e) => {
        e.preventDefault();
        if (email) await onGrant(email, kind);
      }}
    >
      <h2 id="grant-form" style={{ font: "var(--t-title-s)" }}>
        Qualify without a test
      </h2>
      <SelectField
        label="Labeller"
        value={email}
        onChange={setEmail}
        options={[{ value: "", label: emails.length ? "Choose…" : "Nobody is active yet" }, ...emails]}
      />
      <SelectField label="Kind" value={kind} onChange={setKind} options={Object.entries(KIND_QUESTION).map(([value, label]) => ({ value, label }))} />
      <p className="text-[13px] leading-[1.5]" style={{ color: "var(--ink-3)" }}>
        For a kind with no test yet, or someone whose judgement you already trust. Recorded as a grant, never as a score.
      </p>
      <div>
        <button type="submit" className="p-btn p-btn--secondary" disabled={!email}>
          Grant
        </button>
      </div>
    </form>
  );
}

function AddForm({ languages, onAdd }: { languages: string[]; onAdd: (email: string, langs: string[]) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [chosen, setChosen] = useState<string[]>(["en"]);
  const toggle = (code: string) => setChosen((c) => (c.includes(code) ? c.filter((x) => x !== code) : [...c, code]));
  return (
    <form
      className="admin-panel grid content-start gap-3"
      aria-labelledby="add-form"
      onSubmit={async (e) => {
        e.preventDefault();
        await onAdd(email.trim(), chosen);
        setEmail("");
      }}
    >
      <h2 id="add-form" style={{ font: "var(--t-title-s)" }}>
        Add a labeller
      </h2>
      <TextField type="email" required label="Account email" placeholder="name@example.com" value={email} onChange={setEmail} />
      <fieldset>
        <legend className="p-field__label">They read</legend>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {languages.map((code) => (
            <button key={code} type="button" className="p-chip" aria-pressed={chosen.includes(code)} aria-label={langName(code)} onClick={() => toggle(code)}>
              {own(code)}
            </button>
          ))}
        </div>
      </fieldset>
      <p className="text-[13px] leading-[1.5]" style={{ color: "var(--ink-3)" }}>
        They need a Prism account first. Active at once: no application, no test.
      </p>
      <div>
        <button type="submit" className="p-btn p-btn--secondary" disabled={!email || chosen.length === 0}>
          Add
        </button>
      </div>
    </form>
  );
}
