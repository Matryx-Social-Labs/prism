"use client";

/**
 * "Is this report about the record's happening?" (the attach_identity kind): one
 * report against the record Prism put it in (tools/gold_attaches --push). The
 * answers measure the attach thresholds: the same happening, a later
 * development of it, or a different happening — and Not sure.
 *
 * Set in the task frame like the other kinds: the question as the eyebrow, the
 * record as the anchor card, the report with its headline as printed (in its own
 * script) and Prism's English rendering, the answers at the thumb. The three are
 * peers, so none is the ink pill — a primary "Same" would lean the labeller
 * towards it. No keys: a window-wide shortcut once answered for a focused
 * control (2026-09-24).
 */

import type { ReactNode } from "react";

import { AnswerButton, TaskFrame, type Answer } from "@/components/label/parts";
import type { AttachChoice, LabelAttachPair } from "@/lib/api";
import { KIND_QUESTION } from "@/lib/labeller";
import { langName } from "@/lib/languages";

/** The three definite answers, in the words on their buttons. */
export const ATTACH_CHOICES: readonly (readonly [AttachChoice, string])[] = [
  ["same", "Same happening"],
  ["follow_up", "Later development"],
  ["different", "Different happening"],
];

export function AttachTask({
  pair, tag, saving, pending, feedback, onAnswer,
}: {
  pair: LabelAttachPair;
  tag?: string;
  saving: boolean;
  pending?: Answer | null;
  feedback?: ReactNode;
  onAnswer: (answer: AttachChoice | "unsure") => void;
}) {
  const { record, article } = pair;
  const lang = article.language || undefined;
  const material = (
    <>
      <section className="p-card grid gap-1.5" style={{ borderTop: "var(--rule-section) solid var(--ink)" }} aria-label="The record">
        <h2 className="p-eyebrow">The record</h2>
        <p style={{ font: "var(--t-title)", textWrap: "pretty", overflowWrap: "anywhere" }}>{record.headline}</p>
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)", overflowWrap: "anywhere" }}>{record.summary}</p>
        <p className="p-count" style={{ whiteSpace: "normal" }}>first reported {record.first_reported}</p>
      </section>

      <section className="grid gap-2 border-t pt-3" style={{ borderColor: "var(--line)" }} aria-label="The report">
        <h2 className="p-eyebrow">The report</h2>
        <p className="p-count" style={{ whiteSpace: "normal" }}>
          {article.outlet} · {langName(article.language)} · {article.published}
        </p>
        <p lang={lang} style={{ font: "var(--t-title-s)", overflowWrap: "anywhere" }}>{article.title}</p>
        <div className="grid gap-1 pt-1">
          <p className="p-eyebrow">In English · Prism&apos;s rendering</p>
          {/* An English report's headline is often its own; printed twice it reads as a bug. */}
          {article.headline_english !== article.title && (
            <p style={{ font: "var(--t-title-s)", overflowWrap: "anywhere" }}>{article.headline_english}</p>
          )}
          <p style={{ font: "var(--t-body)", color: "var(--ink-2)", overflowWrap: "anywhere" }}>{article.summary_english}</p>
        </div>
      </section>

      <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
        Same if the report tells of the record&apos;s very happening, in any words, figures or language. A later
        development of it is not the same. Anything else, however close the subject, is different.{" "}
        <strong>Not sure</strong> is a real answer.
      </p>
    </>
  );
  return (
    <TaskFrame
      question={KIND_QUESTION.attach_identity}
      tag={tag}
      material={material}
      panel={
        feedback ?? (
          <div className="grid gap-2" role="group" aria-label="Your answer">
            {ATTACH_CHOICES.map(([choice, text]) => (
              <AnswerButton
                key={choice}
                a={choice}
                cls="p-btn--secondary p-btn--lg p-btn--block"
                text={text}
                saving={saving}
                picked={pending}
                onClick={() => onAnswer(choice)}
              />
            ))}
            <AnswerButton
              a="unsure"
              cls="p-btn--ghost min-h-12"
              text="Not sure"
              saving={saving}
              picked={pending}
              onClick={() => onAnswer("unsure")}
            />
          </div>
        )
      }
    />
  );
}
