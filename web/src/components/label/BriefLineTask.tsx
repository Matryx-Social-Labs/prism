"use client";

/**
 * "Does the report say this?" (the brief_support kind): one line of Prism's
 * brief and the report it was written from. The Phase 2 gate on citations
 * (correlation/cites.py, tools/gold_brief_cites) is measured from these answers:
 * a line people say the report does not state is printed as Prism's reading,
 * never as the report's.
 *
 * Not a kind the Label board draws; set in its task frame all the same: the
 * question as the eyebrow, Prism's line as the anchor card, the report's closest
 * passage, the whole report behind a disclosure, the answers at the thumb. "I can't read <language>" is a skip, a
 * fact about the labeller, never a vote.
 */

import type { ReactNode } from "react";

import { AnswerButtons, TaskFrame, type Answer } from "@/components/label/parts";
import type { LabelBriefLine } from "@/lib/api";
import { KIND_QUESTION } from "@/lib/labeller";

export function BriefLineTask({
  line, tag, saving, pending, feedback, onAnswer,
}: {
  line: LabelBriefLine;
  tag?: string;
  saving: boolean;
  pending?: Answer | null;
  feedback?: ReactNode;
  onAnswer: (answer: Answer) => void;
}) {
  const r = line.report;
  const foreign = r.code && r.code !== "en";
  const material = (
    <>
      <figure className="p-card grid gap-1.5" style={{ borderTop: "var(--rule-section) solid var(--ink)" }}>
        <figcaption className="p-eyebrow">Prism&apos;s line</figcaption>
        <blockquote style={{ font: "var(--t-title)", overflowWrap: "anywhere" }}>{line.line}</blockquote>
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>{line.story}</p>
      </figure>

      <section className="grid gap-2 border-t pt-3" style={{ borderColor: "var(--line)" }} aria-label="The report">
        <h2 className="p-eyebrow">The report</h2>
        <p className="p-count" style={{ whiteSpace: "normal" }}>{r.outlet} · {r.language}</p>
        <p style={{ font: "var(--t-title-s)", overflowWrap: "anywhere" }} lang={r.code || undefined}>{r.title}</p>
        <p style={{ font: "var(--t-body)", overflowWrap: "anywhere" }} lang={r.code || undefined}>{r.excerpt}</p>
        <details>
          <summary className="flex min-h-11 cursor-pointer list-none items-center text-[14px] font-semibold [&::-webkit-details-marker]:hidden" style={{ color: "var(--accent)" }}>
            Read the whole report
          </summary>
          <p className="whitespace-pre-line" style={{ font: "var(--t-body)", color: "var(--ink-2)", overflowWrap: "anywhere" }} lang={r.code || undefined}>{r.text}</p>
          {r.url && (
            <a href={r.url} target="_blank" rel="noopener noreferrer" className="p-link mt-2 inline-flex min-h-11 items-center text-[13.5px]">
              Open it on {r.outlet} ↗
            </a>
          )}
        </details>
      </section>

      <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
        Yes only if the report states everything in the line, in any words. A figure, name, cause or judgement the
        report does not state is a No. You are not judging whether the line is true.
      </p>
    </>
  );
  return (
    <TaskFrame
      question={KIND_QUESTION.brief_support}
      tag={tag}
      material={material}
      panel={
        feedback ?? (
          <AnswerButtons
            yes="Yes — the report says this"
            no="No — not what the report says"
            cantRead={foreign ? `I can't read ${r.language}` : undefined}
            saving={saving}
            picked={pending}
            onAnswer={onAnswer}
          />
        )
      }
    />
  );
}
