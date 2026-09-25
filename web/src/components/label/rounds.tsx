"use client";

/**
 * What a practice round and a qualification test show that a work batch does
 * not: after each PRACTICE answer, whether it was right and why — in place of
 * the answers, the material still on screen; at the end of either, the score
 * and the reasons for the ones missed (labeller workspace, phase 3). A test
 * shows nothing until it is over — the server never sends an answer before
 * then, so there is nothing here to hide.
 *
 * Design System v2 · label/Verdict + label/ResultScreen: "Right." and "Not
 * quite." are words, with an icon, on a solid or a dashed rule — no state is
 * conveyed by colour alone (the Legend Rule).
 */

import { EndScreen, Lede, Verdict } from "@/components/label/parts";
import type { LabelFeedback, LabelResult, LabelTask } from "@/lib/api";
import { KIND_QUESTION } from "@/lib/labeller";

/** "1", "1 and 3", "1, 2 and 4". */
const listed = (ns: number[]) => (ns.length < 2 ? ns.join("") : `${ns.slice(0, -1).join(", ")} and ${ns[ns.length - 1]}`);

export function PracticeFeedback({ task, feedback, onNext }: { task: LabelTask; feedback: LabelFeedback; onNext: () => void }) {
  const expected = new Set(feedback.expected);
  // What the right answer WAS, in the task's own terms: which rows should have
  // been ticked (by their numbers, which sit on the rows above), or whether
  // the article credits the quote to this person.
  const yes = expected.has(task.id);
  const rendering = task.rendering;
  const rows = (task.candidates ?? []).flatMap((c, i) => (expected.has(c.id) ? [i + 1] : []));
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
        : rows.length
          ? `The ones to tick: ${listed(rows)}.`
          : "Nothing here should be ticked.";
  return (
    <section aria-live="polite" className="grid gap-2.5">
      <Verdict kind={feedback.correct ? "right" : "wrong"} word={feedback.correct ? "Right." : "Not quite."}>
        <p style={{ color: "var(--ink)" }}>{answer}</p>
        {feedback.explanation && <p style={{ color: "var(--ink-2)" }}>{feedback.explanation}</p>}
      </Verdict>
      <button type="button" onClick={onNext} className="p-btn p-btn--primary p-btn--lg p-btn--block">
        Next question
      </button>
    </section>
  );
}

/** The score at the end of a round: a solid rule for a pass, dashed for a miss.
 *  Counted as "k of n": a round is too few questions for a percent. The pass
 *  mark is the API's. */
export function RoundResult({ result, kind }: { result: LabelResult; kind?: string }) {
  const need = Math.round(result.pass_mark * 100);
  const test = result.purpose === "qualify";
  const question = kind ? KIND_QUESTION[kind] : undefined;
  return (
    <div className="grid gap-4">
      <p className="p-eyebrow">{[test ? "Test" : "Practice", question].filter(Boolean).join(" · ")}</p>
      <EndScreen
        dashed={test && !result.passed}
        title={test ? (result.passed ? "You passed." : "Not this time.") : "Practice round done."}
      >
        <p style={{ font: "var(--t-body-l)" }}>
          <span className="font-mono">{result.right} of {result.total}</span> right · pass mark {need}%
        </p>
        <Lede>
          {test
            ? result.passed
              ? "Work of this kind is now in your workspace."
              : `You need ${need}%. You can take it again in 24 hours, with different questions.`
            : "Practise again as often as you like; the test is scored the same way."}
        </Lede>
        {result.missed.length > 0 && (
          <div className="mt-2">
            <h2 className="p-eyebrow mb-1.5">What you missed</h2>
            <ul>
              {result.missed.map((m) => (
                <li key={m.position} className="border-t py-2.5" style={{ borderColor: "var(--line)", font: "var(--t-body-s)", overflowWrap: "anywhere" }}>
                  {m.about && <p className="font-semibold" style={{ color: "var(--ink)" }}>{m.about}</p>}
                  <p style={{ color: "var(--ink-2)" }}>{m.explanation}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </EndScreen>
    </div>
  );
}

/** The end of a work batch. The hidden-check standing is deliberately not
 *  shown: the API never says which tasks were checks (api/routes/label.answer),
 *  and it does not send the labeller their check score. */
export function DoneScreen({ total, batch, who }: { total: number; batch?: string; who: string }) {
  return (
    <EndScreen title="That's everything.">
      <Lede>
        <span className="font-mono">{total}</span> {total === 1 ? "judgement" : "judgements"}
        {batch ? ` in ${batch}` : " in this batch"}. Thank you{who ? `, ${who}` : ""}.
      </Lede>
    </EndScreen>
  );
}
