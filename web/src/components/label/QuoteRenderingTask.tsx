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
 * Design System v2 · Label board, "Same statement, or a translation?": each
 * quote on its own ink rule with its language and outlet, then the question.
 * Each quote carries its `lang` so the browser shapes Kannada, Tamil or
 * Devanagari in the right face. "I can't read …" is a skip — a fact about the
 * labeller, never a vote — and appears only when a quote is not English.
 */

import type { ReactNode } from "react";

import { AnswerButtons, TaskFrame, type Answer } from "@/components/label/parts";
import type { LabelRendering } from "@/lib/api";
import { langNative } from "@/lib/languages";
import { KIND_QUESTION } from "@/lib/labeller";

export function QuoteRenderingTask({
  rendering, tag, saving, pending, feedback, onAnswer,
}: {
  rendering: LabelRendering;
  tag?: string;
  saving: boolean;
  pending?: Answer | null;
  feedback?: ReactNode;
  onAnswer: (answer: Answer) => void;
}) {
  const same = rendering.question === "same";
  const heading = same
    ? `Is this the same statement by ${rendering.speaker}?`
    : `Did ${rendering.speaker} say this in ${rendering.a.language}?`;
  const quotes = [rendering.a, rendering.b].flatMap((q) => (q ? [q] : []));
  const unreadable = [...new Set(quotes.map((q) => q.language).filter((l) => l !== "English"))];
  const material = (
    <>
      <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{rendering.story}</p>
      <div className="grid gap-2.5">
        {quotes.map((q, i) => (
          <figure key={i} className="grid gap-1.5 pl-3.5" style={{ borderLeft: "var(--rule-section) solid var(--ink)" }}>
            <blockquote lang={q.code || undefined} style={{ font: "italic 400 19px/1.5 var(--font-record)", overflowWrap: "anywhere" }}>
              “{q.quote}”
            </blockquote>
            <figcaption className="p-count" style={{ whiteSpace: "normal" }}>
              {[q.code && q.code !== "en" ? langNative(q.code) : null, q.language, q.outlet].filter(Boolean).join(" · ")}
            </figcaption>
          </figure>
        ))}
      </div>
      <h2 className="border-t pt-3" style={{ font: "600 16px/1.45 var(--font-read)", borderColor: "var(--line-strong)" }}>
        {heading}
      </h2>
      <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
        {same
          ? "Yes if both report the same thing said — a translation reads differently and still counts. No if they are two different things said."
          : `No if ${rendering.a.outlet} translated it from the language ${rendering.speaker} actually spoke. You are not judging whether it is true.`}
      </p>
    </>
  );
  return (
    <TaskFrame
      question={KIND_QUESTION.quote_rendering}
      tag={tag}
      material={material}
      panel={
        feedback ?? (
          <AnswerButtons
            yes={same ? "Yes — the same statement" : `Yes — said in ${rendering.a.language}`}
            no={same ? "No — two different statements" : "No — the outlet translated it"}
            cantRead={unreadable.length ? `I can't read ${unreadable.join(" or ")}` : undefined}
            saving={saving}
            picked={pending}
            onAnswer={onAnswer}
          />
        )
      }
    />
  );
}
