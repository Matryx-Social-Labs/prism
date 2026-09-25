"use client";

/**
 * The approved labeller's workspace, as the page renders it from the API
 * (Design System v2 · Label board, "The workspace"): what is waiting, counted;
 * the batches ready to label; learn and qualify; what is done. A labeller never
 * sees another labeller's answers here — only how many people are on a batch,
 * the anti-anchoring rule the task routes already keep. Every number is the
 * API's; a share of a test is never printed as a percent, because the API sends
 * the best score without the question count it is out of.
 */

import Link from "next/link";

import { ArrowRight } from "@/components/icons";
import { SectionHead } from "@/components/SectionHead";
import {
  KIND_QUESTION,
  LEARNABLE,
  type LabellerBatch,
  type LabellerBatches,
  type LabellerKind,
  type LabellerMe,
} from "@/lib/labeller";

// p-btn--sm is 36px: tall enough for a pointer, not for a thumb.
const SMALL = "p-btn--sm min-h-11 lg:min-h-9";

export function Section({ title, id, sub, hint, children }: { title: string; id?: string; sub?: string; hint?: string; children: React.ReactNode }) {
  const slug = id ?? title.toLowerCase().replace(/[^a-z]+/g, "-");
  return (
    <section id={id} className="scroll-mt-20">
      <SectionHead id={`h-${slug}`} title={title} sub={sub} hint={hint} />
      {children}
    </section>
  );
}

/** The languages this labeller reads, by their English names or their own. */
export const languageNames = (me: LabellerMe, native = false) =>
  me.languages_available.filter((l) => me.languages_read.includes(l.code)).map((l) => (native ? l.native : l.name));

/** A time the way the product prints one: IST, day and month, 24-hour. */
export function ist(iso: string): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "Asia/Kolkata",
  }).formatToParts(new Date(iso));
  const p = Object.fromEntries(parts.map((x) => [x.type, x.value]));
  return `${p.day} ${p.month}, ${p.hour}:${p.minute} IST`;
}

/** What is waiting for this labeller, counted — the same list the founders'
 *  dashboard opens with. Counts, never a percentage; nothing, never a zero. */
function NeedsYou({ batches }: { batches: LabellerBatches }) {
  const tasks = batches.ready.reduce((n, b) => n + Math.max(0, b.eligible - b.answered), 0);
  const tests = (batches.kinds ?? []).filter((k) => k.can_test && !k.qualified).length;
  const items = [
    { href: "#ready", count: tasks, text: tasks === 1 ? "task ready in your languages" : "tasks ready in your languages" },
    { href: "#learn", count: tests, text: tests === 1 ? "test you can take" : "tests you can take" },
  ].filter((i) => i.count > 0);
  return (
    <section aria-labelledby="needs-you">
      <h2 id="needs-you" className="p-eyebrow mb-2">Waiting for you</h2>
      {items.length === 0 ? (
        <p className="border-t py-3" style={{ borderColor: "var(--line)", font: "var(--t-body-s)", color: "var(--ink-2)" }}>
          Nothing right now. New batches in your languages appear here.
        </p>
      ) : (
        <ul className="grid gap-1.5">
          {items.map((i) => (
            <li key={i.href}>
              <a
                href={i.href}
                className="flex min-h-11 items-center gap-2.5 border px-3 py-2.5"
                style={{ borderColor: "var(--line-strong)", borderRadius: "var(--r-md)", color: "var(--ink)" }}
              >
                <span className="p-mono text-[13px] font-medium">{i.count}</span>{" "}
                <span className="min-w-0 flex-1" style={{ font: "500 14px/1.35 var(--font-read)" }}>{i.text}</span>
                <span aria-hidden className="inline-flex" style={{ color: "var(--accent)" }}><ArrowRight size={14} /></span>
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function BatchRow({ batch, onStart }: { batch: LabellerBatch; onStart?: (key: string) => void }) {
  const share = batch.eligible ? Math.min(100, (batch.answered / batch.eligible) * 100) : 0;
  return (
    <li className="grid gap-2 border-t py-4" style={{ borderColor: "var(--line)" }}>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h3 className="min-w-0 flex-[1_1_14rem]" style={{ font: "var(--t-title-s)", overflowWrap: "anywhere" }}>{batch.name}</h3>
        <span className="p-count">
          {batch.answered} of {batch.eligible} done · {batch.labellers} {batch.labellers === 1 ? "labeller" : "labellers"}
        </span>
      </div>
      <p style={{ font: "500 14.5px/1.4 var(--font-read)" }}>{KIND_QUESTION[batch.kind] ?? batch.kind}</p>
      {batch.notes && <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{batch.notes}</p>}
      <div aria-hidden className="h-[3px]" style={{ background: "var(--line)" }}>
        <div className="h-[3px]" style={{ width: `${share}%`, background: "var(--ink)" }} />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {LEARNABLE.includes(batch.kind) && (
          <Link href={`/label/learn/${batch.kind}`} className="p-link inline-flex min-h-11 items-center text-[13.5px]">
            How this task works
          </Link>
        )}
        <span className="flex-1" />
        {onStart && (
          <button type="button" onClick={() => onStart(batch.key)} className={`p-btn p-btn--primary ${SMALL}`}>
            {batch.answered > 0 ? "Continue" : "Start"}
          </button>
        )}
      </div>
    </li>
  );
}

function QualifyRow({ k, onPractise, onTest }: { k: LabellerKind; onPractise: (kind: string) => void; onTest: (kind: string) => void }) {
  const [status, badge] = k.qualified
    ? ["Passed", "p-badge--ink"]
    : k.retake_at || k.attempts > 0
      ? ["Not passed yet", "p-badge--outline"]
      : k.can_test
        ? ["Not taken yet", "p-badge--outline"]
        : ["Test coming soon", "p-badge--dashed"];
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-2 border-t py-3.5" style={{ borderColor: "var(--line)" }}>
      <div className="min-w-0">
        <h3 style={{ font: "600 15px/1.3 var(--font-read)" }}>{KIND_QUESTION[k.kind] ?? k.kind}</h3>
        <p className="p-count">{k.kind}</p>
      </div>
      <span className={`p-badge ${badge} self-start`}>{status}</span>
      {k.retake_at && (
        <p className="col-span-2" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
          You can retake it after <span className="font-mono text-[13px]">{ist(k.retake_at)}</span>, with new questions.
        </p>
      )}
      <div className="col-span-2 flex flex-wrap gap-1.5">
        {LEARNABLE.includes(k.kind) && (
          <Link href={`/label/learn/${k.kind}`} className={`p-btn p-btn--ghost ${SMALL}`}>
            Read the guide
          </Link>
        )}
        {k.can_practise && (
          <button type="button" onClick={() => onPractise(k.kind)} className={`p-btn p-btn--ghost ${SMALL}`}>
            Practise
          </button>
        )}
        {(k.can_test || k.retake_at) && (
          <button type="button" disabled={!k.can_test} onClick={() => onTest(k.kind)} className={`p-btn p-btn--secondary ${SMALL}`}>
            Take the test
          </button>
        )}
      </div>
    </li>
  );
}

export function ActiveWorkspace({
  batches, onStart, onPractise, onTest,
}: {
  batches: LabellerBatches;
  onStart: (key: string) => void;
  onPractise: (kind: string) => void;
  onTest: (kind: string) => void;
}) {
  const kinds = batches.kinds ?? [];
  const n = batches.ready.length;
  return (
    <>
      <NeedsYou batches={batches} />
      {n > 0 && (
        <Section title="Ready to label" id="ready" sub={`${n} ${n === 1 ? "batch" : "batches"}`}>
          <ul>{batches.ready.map((b) => <BatchRow key={b.key} batch={b} onStart={onStart} />)}</ul>
        </Section>
      )}
      {kinds.length > 0 && (
        <Section title="Learn and qualify" id="learn" hint="Each kind of task has a short test. Pass it and that kind of work appears above.">
          <ul>{kinds.map((k) => <QualifyRow key={k.kind} k={k} onPractise={onPractise} onTest={onTest} />)}</ul>
        </Section>
      )}
      {batches.done.length > 0 && (
        <Section title="Done">
          <ul>{batches.done.map((b) => <BatchRow key={b.key} batch={b} />)}</ul>
        </Section>
      )}
    </>
  );
}

/** A refusal from the labeller API, in words: what happened, and the one way on.
 *  Keyed on the API's own `detail` strings (api/routes/labeller.py); anything
 *  else is shown as the API said it. */
export type Explained = { title: string; body?: string; tone: "info" | "error"; action?: "languages" | "learn" };

const EXPLAIN: Record<string, Explained> = {
  "pass this task's test first": { title: "Pass the test first", body: "Pass this kind of task's test and the batch opens here.", tone: "error", action: "learn" },
  "batch is closed": { title: "This batch has closed", body: "It no longer takes answers.", tone: "info" },
  "no tasks in the languages you read": { title: "No tasks in your languages", body: "Add a language you read well, or wait for the next batch.", tone: "error", action: "languages" },
  "your access to this batch was revoked": { title: "Your access to this batch was withdrawn", body: "Write to hello@readprism.news if you think this is a mistake.", tone: "error" },
  "not enough test questions in your languages yet": { title: "Not enough questions in your languages yet", body: "The test opens once it has enough questions in the languages you read.", tone: "info" },
  "you have already passed this test": { title: "You have already passed this test", tone: "info" },
  "your application has not been approved yet": { title: "Your application has not been approved yet", body: "A founder reads every application.", tone: "info" },
  "This browser is blocking storage, which labelling needs. Try a normal window.": {
    title: "Your browser blocked storage",
    body: "Prism keeps your place in a batch in this browser. Allow site storage, or use a normal window, and try again.",
    tone: "error",
  },
};

export function explain(message: string): Explained {
  if (EXPLAIN[message]) return EXPLAIN[message];
  // "you can retake this test after 24 hours" — the hours are the API's.
  if (message.startsWith("you can retake this test after")) {
    return { title: `You ${message.slice(4)}`, body: "Retakes come with new questions.", tone: "info" };
  }
  return { title: "That did not work", body: message, tone: "error" };
}
