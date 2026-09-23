"use client";

/**
 * The labeller workspace: apply, wait for approval, then see every batch you
 * can do and start one (plan: .claude/plans/labeller-workspace.plan.md).
 *
 * Founder decisions 2026-09-23: anyone with a Prism account may APPLY; an admin
 * approves (tools/label_admin); a labeller is shown only tasks in languages
 * they said they read. Starting a batch hands over the same per-batch
 * credential a founder's invite link carries, so /label/<key> is unchanged.
 *
 * Styled as the task page is: rules and type, no cards; mono only for counts;
 * one primary action on the page (Apply), text actions on rows. A labeller
 * never sees another labeller's answers here — only how many people are on a
 * batch, the anti-anchoring rule the task routes already keep.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  KIND_QUESTION,
  LEARNABLE,
  applyAsLabeller,
  fetchLabellerBatches,
  fetchLabellerMe,
  startBatch,
  startPractice,
  startTest,
  type LabellerBatch,
  type LabellerBatches,
  type LabellerKind,
  type LabellerMe,
} from "@/lib/labeller";
import { useSession } from "@/lib/session";

export default function LabellerWorkspace() {
  const session = useSession();
  const router = useRouter();
  // useSession reads storage in an effect, so its first value is null for
  // everyone; without this a signed-in labeller sees "Sign in" flash first.
  const [mounted, setMounted] = useState(false);
  const [me, setMe] = useState<LabellerMe | null>(null);
  const [batches, setBatches] = useState<LabellerBatches | null>(null);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => setMounted(true), []);

  const load = useCallback(async () => {
    if (!session) return;
    try {
      const who = await fetchLabellerMe(session);
      setMe(who);
      setBatches(who.status === "active" ? await fetchLabellerBatches(session) : null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load your workspace");
    }
  }, [session]);

  useEffect(() => {
    void load();
  }, [load]);

  // Every way into a task page: a work batch, a practice round, a test.
  const go = async (open: () => Promise<string>, failed: string) => {
    setError("");
    try {
      router.push(await open());
    } catch (e) {
      setError(e instanceof Error ? e.message : failed);
    }
  };
  const start = (key: string) => session && go(() => startBatch(session, key), "Could not start that batch");
  const practise = (kind: string) => session && go(() => startPractice(session, kind), "Could not start practice");
  const test = (kind: string) => session && go(() => startTest(session, kind), "Could not start the test");

  if (!mounted) return <Shell />;

  return (
    <Shell>
      <h1 className="text-[27px] leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        Label for Prism
      </h1>
      <p className="mt-3 text-[15px] leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
        Every quality check in Prism is measured against answers people give here: whether two reports are the same
        happening, who really said a quote, whether a quote is the speaker&apos;s words or an outlet&apos;s translation.
        Each task is one question, and takes about a minute.
      </p>
      {error && (
        <p role="alert" className="mt-5 border-l-2 pl-3 text-[14px]" style={{ borderColor: "var(--ink)" }}>
          {error}
        </p>
      )}

      {!session && (
        <div className="mt-8">
          <Link href="/signin?next=/label" className="btn btn-primary">
            Sign in to apply
          </Link>
        </div>
      )}

      {session && me && (me.status === "none" || editing) && (
        <ApplyForm
          me={me}
          onDone={async (languages, note) => {
            setError("");
            try {
              await applyAsLabeller(session, languages, note);
              setEditing(false);
              await load();
            } catch (e) {
              setError(e instanceof Error ? e.message : "Could not send your application");
            }
          }}
        />
      )}

      {session && me && me.status === "applied" && !editing && (
        <Section title="Your application is in">
          <p className="text-[15px] leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
            A founder reads every application. Once you are approved, the batches in your languages appear here.
          </p>
          <Languages me={me} onEdit={() => setEditing(true)} />
        </Section>
      )}

      {session && me && (me.status === "paused" || me.status === "removed") && (
        <Section title={me.status === "paused" ? "Your labelling is paused" : "Your labelling has ended"}>
          <p className="text-[15px] leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
            Write to <a className="underline" href="mailto:hello@readprism.news">hello@readprism.news</a> and we will
            tell you why.
          </p>
        </Section>
      )}

      {session && me && me.status === "active" && batches && !editing && (
        <>
          <Languages me={me} onEdit={() => setEditing(true)} />
          <Section title="Ready to label">
            {batches.ready.length === 0 ? (
              <p className="text-[15px]" style={{ color: "var(--ink-muted)" }}>
                Nothing waiting in your languages right now.
              </p>
            ) : (
              <ul>{batches.ready.map((b) => <BatchRow key={b.key} batch={b} onStart={start} />)}</ul>
            )}
          </Section>
          {batches.done.length > 0 && (
            <Section title="Done">
              <ul>{batches.done.map((b) => <BatchRow key={b.key} batch={b} />)}</ul>
            </Section>
          )}
        </>
      )}

      {session && me?.status === "active" && batches?.kinds && batches.kinds.length > 0 && !editing && (
        <Section title="Learn and qualify">
          <p className="mb-3 text-[14px]" style={{ color: "var(--ink-muted)" }}>
            Each kind of task has a short test. Pass it (90%) and that kind of work appears above.
          </p>
          <ul>{batches.kinds.map((k) => <KindRow key={k.kind} k={k} onPractise={practise} onTest={test} />)}</ul>
        </Section>
      )}

      {/* Readable by anyone, approved or not: the guide is the first thing a
          labeller should meet, and waiting for approval is a good time to. */}
      <Section title="Learn the tasks">
        <ul>
          {LEARNABLE.map((kind) => (
            <li key={kind} className="border-t py-3" style={{ borderColor: "var(--line)" }}>
              <Link href={`/label/learn/${kind}`} className="text-[15px] font-semibold underline-offset-4 hover:underline">
                {KIND_QUESTION[kind]}
              </Link>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}

function ApplyForm({ me, onDone }: { me: LabellerMe; onDone: (languages: string[], note: string) => Promise<void> }) {
  const [chosen, setChosen] = useState<string[]>(me.languages_read);
  const [note, setNote] = useState(me.note);
  const [sending, setSending] = useState(false);
  const toggle = (code: string) =>
    setChosen((c) => (c.includes(code) ? c.filter((x) => x !== code) : [...c, code]));
  return (
    <form
      className="mt-8"
      onSubmit={async (e) => {
        e.preventDefault();
        setSending(true);
        await onDone(chosen, note);
        setSending(false);
      }}
    >
      <fieldset>
        <legend className="text-[17px] font-semibold">Which languages do you read well?</legend>
        <p className="mt-1 text-[14px]" style={{ color: "var(--ink-muted)" }}>
          You will only be given tasks in these. Most tasks also need English.
        </p>
        <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
          {me.languages_available.map((l) => (
            <label key={l.code} className="flex min-h-[44px] items-center gap-2.5 text-[15px]">
              <input type="checkbox" checked={chosen.includes(l.code)} onChange={() => toggle(l.code)} />
              <span>{l.name}</span>
              {l.native !== l.name && <span style={{ color: "var(--ink-muted)" }}>{l.native}</span>}
            </label>
          ))}
        </div>
      </fieldset>
      <label className="mt-6 block">
        <span className="text-[15px] font-semibold">Anything we should know? (optional)</span>
        <textarea
          className="mt-2 w-full rounded-[8px] border p-3 text-[15px]"
          style={{ borderColor: "var(--line-strong)", background: "var(--surface)" }}
          rows={3}
          maxLength={500}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </label>
      <button type="submit" className="btn btn-primary mt-6" disabled={sending || chosen.length === 0}>
        {me.status === "none" ? "Apply" : "Save my languages"}
      </button>
    </form>
  );
}

function Languages({ me, onEdit }: { me: LabellerMe; onEdit: () => void }) {
  const names = me.languages_available.filter((l) => me.languages_read.includes(l.code)).map((l) => l.name);
  return (
    <p className="mt-4 text-[14px]" style={{ color: "var(--ink-muted)" }}>
      You read: {names.join(", ")} ·{" "}
      <button type="button" className="font-semibold underline-offset-4 hover:underline" style={{ color: "var(--accent)" }} onClick={onEdit}>
        Change
      </button>
    </p>
  );
}

function BatchRow({ batch, onStart }: { batch: LabellerBatch; onStart?: (key: string) => void }) {
  return (
    <li className="border-t py-4" style={{ borderColor: "var(--line)" }}>
      <p className="text-[16px] font-semibold">{batch.name}</p>
      <p className="mt-0.5 text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
        {KIND_QUESTION[batch.kind] ?? batch.kind}
      </p>
      {batch.notes && <p className="mt-1 text-[14px]" style={{ color: "var(--ink-muted)" }}>{batch.notes}</p>}
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
          {batch.answered} of {batch.eligible} done · {batch.labellers} {batch.labellers === 1 ? "labeller" : "labellers"}
        </span>
        {LEARNABLE.includes(batch.kind) && (
          <Link href={`/label/learn/${batch.kind}`} className="text-[14px] underline-offset-4 hover:underline" style={{ color: "var(--ink-muted)" }}>
            How this task works
          </Link>
        )}
        {onStart && (
          <button
            type="button"
            onClick={() => onStart(batch.key)}
            className="text-[14px] font-semibold underline-offset-4 hover:underline"
            style={{ color: "var(--accent)" }}
          >
            {batch.answered > 0 ? "Continue" : "Start"}
          </button>
        )}
      </div>
    </li>
  );
}

function KindRow({ k, onPractise, onTest }: { k: LabellerKind; onPractise: (kind: string) => void; onTest: (kind: string) => void }) {
  const status = k.qualified
    ? "Passed"
    : k.retake_at
      ? `Best so far ${Math.round((k.best_score ?? 0) * 100)}% · you can retake it after ${new Date(k.retake_at).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}`
      : k.can_test
        ? k.attempts > 0 ? "Not passed yet" : "Not taken yet"
        : "Test coming soon";
  return (
    <li className="border-t py-4" style={{ borderColor: "var(--line)" }}>
      <p className="text-[16px] font-semibold">{KIND_QUESTION[k.kind] ?? k.kind}</p>
      <p className="mt-0.5 text-[14px]" style={{ color: "var(--ink-muted)" }}>{status}</p>
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[14px]">
        {LEARNABLE.includes(k.kind) && (
          <Link href={`/label/learn/${k.kind}`} className="underline-offset-4 hover:underline" style={{ color: "var(--ink-muted)" }}>
            Read the guide
          </Link>
        )}
        {k.can_practise && (
          <button type="button" onClick={() => onPractise(k.kind)} className="font-semibold underline-offset-4 hover:underline" style={{ color: "var(--accent)" }}>
            Practise
          </button>
        )}
        {k.can_test && (
          <button type="button" onClick={() => onTest(k.kind)} className="font-semibold underline-offset-4 hover:underline" style={{ color: "var(--accent)" }}>
            Take the test
          </button>
        )}
      </div>
    </li>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-10">
      <h2 className="mb-3 text-[17px] font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function Shell({ children }: { children?: React.ReactNode }) {
  // The task page's measure: a focused surface, not a reading river.
  return <main className="mx-auto min-h-dvh w-full max-w-[720px] px-5 pb-24 pt-6 sm:px-8">{children}</main>;
}
