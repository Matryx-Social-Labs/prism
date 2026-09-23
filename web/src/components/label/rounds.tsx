"use client";

/**
 * What a practice round and a qualification test show that a work batch does
 * not: after each PRACTICE answer, whether it was right and why; at the end of
 * either, the score and the reasons for the ones missed (labeller workspace,
 * phase 3). A test shows nothing until it is over — the server never sends an
 * answer before then, so there is nothing here to hide.
 *
 * Styled as the task page is: rules and type, no colour for right and wrong.
 * "Right" and "Not quite" are words, carried by the rule's weight — the Legend
 * Rule (DESIGN.md) says no state is conveyed by colour alone.
 */

import Link from "next/link";

import type { LabelFeedback, LabelResult, LabelTask } from "@/lib/api";

export function PracticeFeedback({ task, feedback, onNext }: { task: LabelTask; feedback: LabelFeedback; onNext: () => void }) {
  const expected = new Set(feedback.expected);
  // What the right answer WAS, in the task's own terms: which reports should
  // have been ticked, or whether the article credits the quote to this person.
  const answer = task.claim
    ? expected.has(task.id)
      ? `Yes — the article credits these words to ${task.claim.speaker}.`
      : `No — the article does not credit these words to ${task.claim.speaker}.`
    : (task.candidates ?? []).filter((c) => expected.has(c.id)).map((c) => c.title);
  return (
    <section
      aria-live="polite"
      className="mt-8 pl-4"
      style={{ borderLeft: `${feedback.correct ? 2 : 4}px solid var(--ink)` }}
    >
      <p className="text-[17px] font-semibold">{feedback.correct ? "Right." : "Not quite."}</p>
      {typeof answer === "string" ? (
        <p className="mt-2 text-[15px]">{answer}</p>
      ) : answer.length ? (
        <div className="mt-2 text-[15px]">
          <p>The ones to tick:</p>
          <ul className="mt-1 list-disc pl-5">{answer.map((t) => <li key={t}>{t}</li>)}</ul>
        </div>
      ) : (
        <p className="mt-2 text-[15px]">Nothing here should be ticked.</p>
      )}
      {feedback.explanation && (
        <p className="mt-3 text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>{feedback.explanation}</p>
      )}
      <button type="button" onClick={onNext} className="btn btn-primary mt-5">
        Next question
      </button>
    </section>
  );
}

export function RoundResult({ result }: { result: LabelResult }) {
  const pct = Math.round(result.score * 100);
  const need = Math.round(result.pass_mark * 100);
  const test = result.purpose === "qualify";
  return (
    <section className="mt-10">
      <h1 className="text-[27px] leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        {test ? (result.passed ? "You passed." : "Not this time.") : "Practice round done."}
      </h1>
      <p className="mt-3 text-[16px]">
        {result.right} of {result.total} right{" "}
        <span className="font-mono text-[13px]" style={{ color: "var(--ink-muted)" }}>({pct}%)</span>
      </p>
      <p className="mt-2 text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
        {test
          ? result.passed
            ? "Work of this kind is now on your dashboard."
            : `You need ${need}%. You can take it again in 24 hours, with different questions.`
          : "Practise again as often as you like; the test is scored the same way."}
      </p>
      {result.missed.length > 0 && (
        <div className="mt-8">
          <h2 className="text-[17px] font-semibold">The ones you missed, and why</h2>
          <ul className="mt-2">
            {result.missed.map((m) => (
              <li key={m.position} className="border-t py-3" style={{ borderColor: "var(--line)" }}>
                {m.about && <p className="text-[15px] font-medium">{m.about}</p>}
                <p className="mt-1 text-[14.5px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>{m.explanation}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
      <Link href="/label" className="btn btn-secondary mt-8 inline-flex">
        Back to your workspace
      </Link>
    </section>
  );
}
