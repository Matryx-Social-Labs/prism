"use client";

/**
 * The quote-rendering task (labeller workspace, phase 4): one of two yes/no
 * questions the quote verdicts need a person to answer before any reader sees
 * them (enrichment/renderings.py, tools/gold_renderings).
 *
 *   same    — are these two quotes, in two languages, the same statement?
 *   spoken  — did the speaker say these words in the language printed, or did
 *             the outlet translate them?
 *
 * Each quote carries its `lang` so the browser shapes Kannada, Tamil or
 * Devanagari in the right face. "I can't read this" is a skip — a fact about
 * the labeller, never a vote about the quote. Set with the story task's parts:
 * the question as the eyebrow, the quotes, the sticky answer footer.
 */

import { AnswerButtons, QuoteInContext } from "@/components/label/parts";
import type { LabelRendering } from "@/lib/api";

export function QuoteRenderingTask({
  rendering, saving, onAnswer,
}: {
  rendering: LabelRendering;
  saving: boolean;
  onAnswer: (verdict: "yes" | "no" | "unsure" | "skip") => void;
}) {
  const same = rendering.question === "same";
  const heading = same
    ? `Is this the same statement by ${rendering.speaker}?`
    : `Did ${rendering.speaker} say this in ${rendering.a.language}?`;
  const quotes = [rendering.a, rendering.b].flatMap((q) => (q ? [q] : []));
  const unreadable = [...new Set(quotes.map((q) => q.language).filter((l) => l !== "English"))];
  return (
    <>
      <h1 className="p-eyebrow">{heading}</h1>
      <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{rendering.story}</p>
      <div className="grid gap-3">
        {quotes.map((q, i) => (
          <div key={i} className="p-card">
            <QuoteInContext quote={q.quote} code={q.code} caption={[q.language, q.outlet]} />
          </div>
        ))}
      </div>
      <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
        {same
          ? "Yes if both report the same thing said — a translation reads differently and still counts. No if they are two different things said."
          : `No if ${rendering.a.outlet} translated it from the language ${rendering.speaker} actually spoke. You are not judging whether it is true.`}
      </p>
      <AnswerButtons
        yes={same ? "Yes — the same statement" : `Yes — said in ${rendering.a.language}`}
        no={same ? "No — two different statements" : "No — the outlet translated it"}
        cantRead={unreadable.length ? `I can't read ${unreadable.join(" or ")}` : undefined}
        saving={saving}
        onYes={() => onAnswer("yes")}
        onNo={() => onAnswer("no")}
        onUnsure={() => onAnswer("unsure")}
        onCantRead={() => onAnswer("skip")}
      />
    </>
  );
}
