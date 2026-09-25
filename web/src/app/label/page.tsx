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
 * Design System v2 · Label flow board: signed out (the pitch, one button),
 * apply (languages with their own names; Apply waits for one), applied and
 * waiting (the guides open now, and only now), the workspace (what is waiting,
 * counted; batches; each kind's standing in words; refusals in words), and the
 * end states for a paused or removed labeller.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ArrowRight } from "@/components/icons";
import { SectionHead } from "@/components/SectionHead";
import { Alert, Checkbox, TextField } from "@/components/ui";
import { Column, EndScreen, LabelStrip, Lede, Small, Title } from "@/components/label/parts";
import { ActiveWorkspace, Section, explain, languageNames, type Explained } from "@/components/label/Workspace";
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

const STEPS = [
  "Apply with the languages you read well",
  "A founder reads your application",
  "Read a short guide, practise, pass a test",
  "Work through batches, one question at a time",
];

export default function LabellerWorkspace() {
  const session = useSession();
  const router = useRouter();
  // useSession reads storage in an effect, so its first value is null for
  // everyone; without this a signed-in labeller sees "Sign in" flash first.
  const [mounted, setMounted] = useState(false);
  const [me, setMe] = useState<LabellerMe | null>(null);
  const [batches, setBatches] = useState<LabellerBatches | null>(null);
  const [editing, setEditing] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [refused, setRefused] = useState<Explained | null>(null);

  useEffect(() => setMounted(true), []);

  const load = useCallback(async () => {
    if (!session) return;
    setLoadFailed(false);
    try {
      const who = await fetchLabellerMe(session);
      setMe(who);
      setBatches(who.status === "active" ? await fetchLabellerBatches(session) : null);
    } catch {
      setLoadFailed(true);
    }
  }, [session]);

  useEffect(() => {
    void load();
  }, [load]);

  // Every way into a task page: a work batch, a practice round, a test.
  const go = async (open: () => Promise<string>, failed: string) => {
    setRefused(null);
    try {
      router.push(await open());
    } catch (e) {
      setRefused(explain(e instanceof Error ? e.message : failed));
    }
  };
  const start = (key: string) => session && go(() => startBatch(session, key), "Could not start that batch");
  const practise = (kind: string) => session && go(() => startPractice(session, kind), "Could not start practice");
  const test = (kind: string) => session && go(() => startTest(session, kind), "Could not start the test");
  const apply = async (languages: string[], note: string) => {
    if (!session) return;
    await applyAsLabeller(session, languages, note);
    setEditing(false);
    await load();
  };

  if (!mounted) return <Shell />;

  if (!session) {
    return (
      <Shell>
        <Title big>Label for Prism</Title>
        <Lede>
          Prism groups reports from many outlets and languages into one record per story. Labellers check that work by
          hand. Each task is one question, about a minute, in the languages you read.
        </Lede>
        <ol className="grid" style={{ borderTop: "var(--rule-section) solid var(--ink)" }}>
          {STEPS.map((step, i) => (
            <li key={step} className="grid grid-cols-[32px_minmax(0,1fr)] border-b py-3" style={{ borderColor: "var(--line)", font: "var(--t-body-s)" }}>
              <span className="p-mono text-[12px]" style={{ color: "var(--ink)" }}>{String(i + 1).padStart(2, "0")}</span>
              {step}
            </li>
          ))}
        </ol>
        <div>
          <Link href="/signin?next=/label" className="p-btn p-btn--primary p-btn--lg w-full lg:w-auto">
            Sign in to apply
          </Link>
        </div>
        <Small>The guides open after you sign in and apply.</Small>
      </Shell>
    );
  }

  const email = session.email;

  if (loadFailed) {
    return (
      <Shell email={email}>
        <Alert
          tone="error"
          title="Your workspace could not load"
          action={<button type="button" className="p-btn p-btn--secondary p-btn--sm min-h-11 lg:min-h-9" onClick={() => void load()}>Try again</button>}
        >
          Prism did not answer. Nothing you&apos;ve done is lost.
        </Alert>
      </Shell>
    );
  }

  if (!me) {
    return (
      <Shell email={email}>
        <div className="grid gap-3" role="status" aria-busy="true">
          <span className="p-skel h-[34px] w-[60%]" />
          <span className="p-skel h-3.5 w-[40%]" />
          <span className="p-skel h-24" />
          <span className="sr-only">Loading your workspace…</span>
        </div>
      </Shell>
    );
  }

  const guides = READS_GUIDES.includes(me.status) && (
    <Section title="Learn the tasks">
      <ul>
        {LEARNABLE.map((kind) => (
          <li key={kind} className="border-b" style={{ borderColor: "var(--line)" }}>
            <Link href={`/label/learn/${kind}`} className="flex min-h-[52px] items-center gap-2.5" style={{ color: "var(--ink)", font: "var(--t-title-s)" }}>
              <span className="min-w-0 flex-1">{KIND_QUESTION[kind]}</span>
              <ArrowRight size={16} />
            </Link>
          </li>
        ))}
      </ul>
    </Section>
  );

  if (me.status === "none" || (editing && me.status === "applied")) {
    return (
      <Shell email={email}>
        <ApplyForm me={me} onApply={apply} onCancel={editing ? () => setEditing(false) : undefined} />
        {me.status === "none" && <Small>A short guide to each kind of task opens once you have applied.</Small>}
      </Shell>
    );
  }

  if (me.status === "applied") {
    return (
      <Shell email={email}>
        <Title>Your application is in</Title>
        <Lede>A founder reads every application. Once you are approved, the batches in your languages appear here.</Lede>
        <p style={{ font: "var(--t-body-s)" }}>
          You read: {languageNames(me, true).join(", ")} · <ChangeButton onClick={() => setEditing(true)} />
        </p>
        {guides}
      </Shell>
    );
  }

  if (me.status === "paused" || me.status === "removed") {
    return (
      <Shell email={email}>
        <EndScreen title={me.status === "paused" ? "Your labelling is paused" : "Your labelling has ended"} action={null}>
          <Lede>
            {me.status === "removed" && "Your answers are kept. "}
            Write to <a className="p-link" href="mailto:hello@readprism.news">hello@readprism.news</a> and we will tell you why.
          </Lede>
        </EndScreen>
        {guides}
      </Shell>
    );
  }

  return (
    <Shell email={email} wide>
      <SectionHead
        id="h-label"
        as="h1"
        title="Your workspace"
        sub={`You read: ${languageNames(me).join(", ")}`}
        right={!editing && <ChangeButton onClick={() => setEditing(true)} />}
      />
      {refused && (
        <Alert
          tone={refused.tone}
          title={refused.title}
          action={
            refused.action === "languages" ? (
              <button type="button" className="p-btn p-btn--secondary p-btn--sm min-h-11 lg:min-h-9" onClick={() => { setRefused(null); setEditing(true); }}>
                Change languages
              </button>
            ) : refused.action === "learn" ? (
              <a href="#learn" className="p-btn p-btn--secondary p-btn--sm min-h-11 lg:min-h-9">Take the test</a>
            ) : undefined
          }
        >
          {refused.body}
        </Alert>
      )}
      {editing && <ApplyForm me={me} onApply={apply} onCancel={() => setEditing(false)} />}
      {batches && !editing && <ActiveWorkspace batches={batches} onStart={start} onPractise={practise} onTest={test} />}
      {!editing && guides}
    </Shell>
  );
}

function ChangeButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" className="p-link text-[13.5px]" style={{ padding: "12px 4px", margin: "-12px -4px" }} onClick={onClick}>
      Change
    </button>
  );
}

function ApplyForm({
  me, onApply, onCancel,
}: {
  me: LabellerMe;
  onApply: (languages: string[], note: string) => Promise<void>;
  onCancel?: () => void;
}) {
  const [chosen, setChosen] = useState<string[]>(me.languages_read);
  const [note, setNote] = useState(me.note);
  const [sending, setSending] = useState(false);
  const [failed, setFailed] = useState(false);
  const first = me.status === "none";
  const toggle = (code: string) =>
    setChosen((c) => (c.includes(code) ? c.filter((x) => x !== code) : [...c, code]));
  return (
    <form
      className="grid gap-5"
      onSubmit={async (e) => {
        e.preventDefault();
        setSending(true);
        setFailed(false);
        try {
          await onApply(chosen, note);
        } catch {
          setFailed(true);
        } finally {
          setSending(false);
        }
      }}
    >
      <div className="grid gap-1.5">
        <Title as={me.status === "active" ? "h2" : "h1"}>Which languages do you read well?</Title>
        <Lede>You will only be given tasks in these. Most tasks also need English.</Lede>
      </div>
      {failed && (
        <Alert tone="error" title={first ? "Your application did not send" : "Your languages did not save"}>
          Your answers are still here; try again.
        </Alert>
      )}
      <fieldset className="grid grid-cols-1 gap-x-4 border-t sm:grid-cols-2" style={{ borderColor: "var(--line)" }}>
        <legend className="sr-only">Languages</legend>
        {me.languages_available.map((l) => (
          <div key={l.code} className="border-b" style={{ borderColor: "var(--line)" }}>
            <Checkbox checked={chosen.includes(l.code)} onChange={() => toggle(l.code)} native={l.native !== l.name ? l.native : null}>
              {l.name}
            </Checkbox>
          </div>
        ))}
      </fieldset>
      <TextField multiline rows={3} maxLength={500} label="Anything we should know? (optional)" value={note} onChange={setNote} />
      <div className="grid gap-2">
        <div className="flex flex-wrap gap-2">
          <button
            type="submit"
            className="p-btn p-btn--primary p-btn--lg w-full lg:w-auto"
            disabled={sending || chosen.length === 0}
            aria-busy={sending || undefined}
          >
            {sending ? (first ? "Applying…" : "Saving…") : first ? "Apply" : "Save my languages"}
          </button>
          {onCancel && (
            <button type="button" className="p-btn p-btn--ghost p-btn--lg w-full lg:w-auto" onClick={onCancel} disabled={sending}>
              Cancel
            </button>
          )}
        </div>
        {chosen.length === 0 && <Small>Tick at least one language to {first ? "apply" : "save"}.</Small>}
      </div>
    </form>
  );
}

function Shell({ children, email, wide = false }: { children?: React.ReactNode; email?: string; wide?: boolean }) {
  // The layout already provides <main>; this is the label bar and the column.
  return (
    <div className="flex min-h-dvh w-full flex-col">
      <LabelStrip email={email} />
      <Column wide={wide}>{children}</Column>
    </div>
  );
}
