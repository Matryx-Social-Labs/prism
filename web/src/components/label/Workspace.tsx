"use client";

/**
 * The approved labeller's workspace, as the page renders it from the API
 * (Design System v2 · labeller Workspace): what is waiting, counted; the batches
 * ready to label; learn and qualify; what is done. A labeller never sees another
 * labeller's answers here — only how many people are on a batch, the
 * anti-anchoring rule the task routes already keep. Every number is the API's.
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

export function Section({ title, id, hint, children }: { title: string; id?: string; hint?: string; children: React.ReactNode }) {
  const slug = id ?? title.toLowerCase().replace(/[^a-z]+/g, "-");
  return (
    <section id={id} className="scroll-mt-20">
      <SectionHead id={`h-${slug}`} title={title} hint={hint} />
      {children}
    </section>
  );
}

/** "You read: English, Kannada · Change" — the language gate, as a provenance strip. */
export function Languages({ me, onEdit }: { me: LabellerMe; onEdit: () => void }) {
  const names = me.languages_available.filter((l) => me.languages_read.includes(l.code)).map((l) => l.name);
  return (
    <p className="p-sechead__sub">
      You read: {names.join(", ")} ·{" "}
      <button type="button" className="p-link" style={{ padding: "12px 4px", margin: "-12px -4px" }} onClick={onEdit}>
        Change
      </button>
    </p>
  );
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
        <p className="p-alert p-alert--info">Nothing right now. New batches in your languages appear here.</p>
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
        <h3 className="min-w-0 flex-[1_1_14rem]" style={{ font: "var(--t-title-s)" }}>{batch.name}</h3>
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
    : k.retake_at
      ? [
          `Best so far ${Math.round((k.best_score ?? 0) * 100)}% · you can retake it after ${new Date(k.retake_at).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}`,
          "p-badge--outline",
        ]
      : k.can_test
        ? [k.attempts > 0 ? "Not passed yet" : "Not taken yet", "p-badge--outline"]
        : ["Test coming soon", "p-badge--dashed"];
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-2 border-t py-3.5" style={{ borderColor: "var(--line)" }}>
      <div className="min-w-0">
        <h3 style={{ font: "600 15px/1.3 var(--font-read)" }}>{KIND_QUESTION[k.kind] ?? k.kind}</h3>
        <p className="p-count">{k.kind}</p>
      </div>
      <span className={`p-badge ${badge} max-w-[20ch] self-start`} style={{ whiteSpace: "normal" }}>{status}</span>
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
        {k.can_test && (
          <button type="button" onClick={() => onTest(k.kind)} className={`p-btn p-btn--secondary ${SMALL}`}>
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
  return (
    <>
      <NeedsYou batches={batches} />
      <Section title="Ready to label" id="ready">
        {batches.ready.length === 0 ? (
          <p className="border-t py-4" style={{ borderColor: "var(--line)", font: "var(--t-body)", color: "var(--ink-2)" }}>
            Nothing waiting in your languages right now.
          </p>
        ) : (
          <ul>{batches.ready.map((b) => <BatchRow key={b.key} batch={b} onStart={onStart} />)}</ul>
        )}
      </Section>
      {kinds.length > 0 && (
        <Section title="Learn and qualify" id="learn" hint="Each kind of task has a short test. Pass it (90%) and that kind of work appears above.">
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
