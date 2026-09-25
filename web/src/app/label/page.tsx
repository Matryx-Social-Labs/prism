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
 * Design System v2 · labeller Workspace: the brand strip, "Your workspace" under
 * the section rule with the languages as its provenance line, then the
 * sections in components/label/Workspace. Everyone else — a stranger, an
 * applicant, a paused labeller — gets the same shell and the pitch.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { SectionHead } from "@/components/SectionHead";
import { LabelStrip } from "@/components/label/parts";
import { ActiveWorkspace, Languages, Section } from "@/components/label/Workspace";
import {
  KIND_QUESTION,
  LEARNABLE,
  READS_GUIDES,
  applyAsLabeller,
  fetchLabellerBatches,
  fetchLabellerMe,
  startBatch,
  startPractice,
  startTest,
  type LabellerBatches,
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

  const active = !!session && me?.status === "active";

  return (
    <Shell>
      {active ? (
        <div className="p-sechead">
          <div className="min-w-0">
            <h1 className="p-sechead__title">Your workspace</h1>
            {!editing && me && <Languages me={me} onEdit={() => setEditing(true)} />}
          </div>
        </div>
      ) : (
        <div>
          <SectionHead id="h-label" as="h1" title="Label for Prism" />
          <p className="max-w-[60ch]" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
            Every quality check in Prism is measured against answers people give here: whether two reports are the same
            happening, who really said a quote, whether a quote is the speaker&apos;s words or an outlet&apos;s translation.
            Each task is one question, and takes about a minute.
          </p>
        </div>
      )}
      {error && (
        <p role="alert" className="p-alert p-alert--error">
          {error}
        </p>
      )}

      {!session && (
        <div>
          <Link href="/signin?next=/label" className="p-btn p-btn--primary">
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
          <p style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
            A founder reads every application. Once you are approved, the batches in your languages appear here.
          </p>
          <div className="mt-3">
            <Languages me={me} onEdit={() => setEditing(true)} />
          </div>
        </Section>
      )}

      {session && me && (me.status === "paused" || me.status === "removed") && (
        <Section title={me.status === "paused" ? "Your labelling is paused" : "Your labelling has ended"}>
          <p style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
            Write to <a className="p-link" href="mailto:hello@readprism.news">hello@readprism.news</a> and we will
            tell you why.
          </p>
        </Section>
      )}

      {active && batches && !editing && (
        <ActiveWorkspace batches={batches} onStart={start} onPractise={practise} onTest={test} />
      )}

      {/* For anyone who has applied, approved or not — waiting for approval is
          a good time to read them — and for nobody else: the guides are how we
          judge the work, so a stranger does not get them (founder, 2026-09-23;
          the API enforces the same rule, this only stops offering the links). */}
      {me && READS_GUIDES.includes(me.status) && (
        <Section title="Learn the tasks">
          <ul>
            {LEARNABLE.map((kind) => (
              <li key={kind} className="border-t" style={{ borderColor: "var(--line)" }}>
                <Link href={`/label/learn/${kind}`} className="p-link flex min-h-11 items-center text-[15px]">
                  {KIND_QUESTION[kind]}
                </Link>
              </li>
            ))}
          </ul>
        </Section>
      )}
      {session && me?.status === "none" && (
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
          A short guide to each kind of task opens once you have applied.
        </p>
      )}
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
      className="grid gap-6"
      onSubmit={async (e) => {
        e.preventDefault();
        setSending(true);
        await onDone(chosen, note);
        setSending(false);
      }}
    >
      <fieldset>
        <legend className="p-field__label" style={{ fontSize: 17 }}>Which languages do you read well?</legend>
        <p className="p-field__hint mt-1">You will only be given tasks in these. Most tasks also need English.</p>
        <div className="mt-2 grid grid-cols-2 gap-x-6 sm:grid-cols-3">
          {me.languages_available.map((l) => (
            <label key={l.code} className="p-check items-center">
              <input type="checkbox" checked={chosen.includes(l.code)} onChange={() => toggle(l.code)} />
              <span>{l.name}</span>
              {l.native !== l.name && <span style={{ color: "var(--ink-3)" }}>{l.native}</span>}
            </label>
          ))}
        </div>
      </fieldset>
      <label className="p-field">
        <span className="p-field__label">Anything we should know? (optional)</span>
        <textarea
          className="p-input py-3"
          rows={3}
          maxLength={500}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </label>
      <div>
        <button type="submit" className="p-btn p-btn--primary" disabled={sending || chosen.length === 0}>
          {me.status === "none" ? "Apply" : "Save my languages"}
        </button>
      </div>
    </form>
  );
}

function Shell({ children }: { children?: React.ReactNode }) {
  // The task page's measure: a focused surface, not a reading river. The
  // layout already provides <main>; this is the column.
  return (
    <div className="mx-auto grid min-h-dvh w-full max-w-[720px] content-start gap-7 px-4 pb-12 pt-6">
      <LabelStrip />
      {children}
    </div>
  );
}
