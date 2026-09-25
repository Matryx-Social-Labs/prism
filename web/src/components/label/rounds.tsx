"use client";

/**
 * What a practice round and a qualification test show that a work batch does
 * not: after each PRACTICE answer, whether it was right and why; at the end of
 * either, the score and the reasons for the ones missed (labeller workspace,
 * phase 3). A test shows nothing until it is over — the server never sends an
 * answer before then, so there is nothing here to hide. And the end of a batch.
 *
 * Design System v2 · label/Verdict + label/ResultScreen: "Right" and "Not
 * quite" are words, with an icon, on a solid or a dashed rule — no state is
 * conveyed by colour alone (the Legend Rule).
 */

import Link from "next/link";

import { Verdict } from "@/components/label/parts";
import type { LabelFeedback, LabelResult, LabelTask } from "@/lib/api";

export function PracticeFeedback({ task, feedback, onNext }: { task: LabelTask; feedback: LabelFeedback; onNext: () => void }) {
  const expected = new Set(feedback.expected);
  // What the right answer WAS, in the task's own terms: which reports should
  // have been ticked, or whether the article credits the quote to this person.
  const yes = expected.has(task.id);
  const rendering = task.rendering;
  const answer = task.line
    ? yes
      ? "Yes — the report says this."
      : "No — the report does not say this."
    : task.claim
    ? yes
      ? `Yes — the article credits these words to ${task.claim.speaker}.`
      : `No — the article does not credit these words to ${task.claim.speaker}.`
    : rendering
      ? rendering.question === "same"
        ? yes ? "Yes — the same statement, in two languages." : "No — two different things said."
        : yes
          ? `Yes — ${rendering.speaker} said it in ${rendering.a.language}.`
          : `No — ${rendering.a.outlet} translated it.`
      : (task.candidates ?? []).filter((c) => expected.has(c.id)).map((c) => c.title);
  return (
    <section aria-live="polite" className="grid gap-4 pt-2">
      <Verdict kind={feedback.correct ? "right" : "wrong"} word={feedback.correct ? "Right." : "Not quite."}>
        {typeof answer === "string" ? (
          <p style={{ color: "var(--ink)" }}>{answer}</p>
        ) : answer.length ? (
          <div style={{ color: "var(--ink)" }}>
            <p>The ones to tick:</p>
            <ul className="mt-1 list-disc pl-5">{answer.map((t) => <li key={t}>{t}</li>)}</ul>
          </div>
        ) : (
          <p style={{ color: "var(--ink)" }}>Nothing here should be ticked.</p>
        )}
        {feedback.explanation && <p style={{ color: "var(--ink-2)" }}>{feedback.explanation}</p>}
      </Verdict>
      <div>
        <button type="button" onClick={onNext} className="p-btn p-btn--primary p-btn--lg">
          Next question
        </button>
      </div>
    </section>
  );
}

/** The score at the end of a round: a solid rule for a pass, dashed for a miss.
 *  Counted as "k of n": a round is too few questions for a percent. */
export function RoundResult({ result }: { result: LabelResult }) {
  const need = Math.round(result.pass_mark * 100);
  const test = result.purpose === "qualify";
  const solid = result.passed || !test;
  return (
    <section className="grid gap-6 pt-8">
      <div className="pt-3.5" style={{ borderTop: `var(--rule-section) ${solid ? "solid" : "dashed"} var(--ink)` }}>
        <h1 style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>
          {test ? (result.passed ? "You passed." : "Not this time.") : "Practice round done."}
        </h1>
        <p className="mt-2" style={{ font: "var(--t-body-l)" }}>
          <span className="font-mono">{result.right} of {result.total}</span> right · pass mark {need}%
        </p>
        <p className="mt-1.5" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
          {test
            ? result.passed
              ? "Work of this kind is now on your dashboard."
              : `You need ${need}%. You can take it again in 24 hours, with different questions.`
            : "Practise again as often as you like; the test is scored the same way."}
        </p>
      </div>
      {result.missed.length > 0 && (
        <div>
          <h2 className="p-eyebrow mb-1.5">The ones you missed, and why</h2>
          <ul>
            {result.missed.map((m) => (
              <li key={m.position} className="border-t py-2.5" style={{ borderColor: "var(--line)", font: "var(--t-body-s)" }}>
                {m.about && <p className="font-semibold" style={{ color: "var(--ink)" }}>{m.about}</p>}
                <p style={{ color: "var(--ink-2)" }}>{m.explanation}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div>
        <Link href="/label" className="p-btn p-btn--primary">
          Back to your workspace
        </Link>
      </div>
    </section>
  );
}

/** The end of a work batch. The hidden-check score is deliberately not shown:
 *  the API never says which tasks were checks (api/routes/label.answer). */
export function DoneScreen({ total, who }: { total: number; who: string }) {
  return (
    <section className="grid gap-4 pt-16">
      <h1 style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>That&apos;s everything.</h1>
      <p style={{ font: "var(--t-body-l)", color: "var(--ink-2)" }}>
        <span className="font-mono">{total}</span> {total === 1 ? "judgement" : "judgements"} in this batch. Thank you
        {who ? `, ${who}` : ""}.
      </p>
      <div>
        <Link href="/label" className="p-btn p-btn--primary">
          Back to your workspace
        </Link>
      </div>
    </section>
  );
}
