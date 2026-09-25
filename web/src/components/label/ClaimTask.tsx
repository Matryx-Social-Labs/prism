"use client";

/**
 * The claim task: a quote, where it sits in the article, and who the extractor
 * says said it (Design System v2 · Label board, "Who said this?").
 *
 * THE VERBATIM CHECK CANNOT DECIDE THIS. A sentence can be copied exactly from
 * the article and still be put in the wrong mouth — the quote matches, the
 * attribution is a lie, and nothing downstream can tell. That is why a person
 * reads it.
 *
 * The quote is shown INSIDE its surrounding sentences rather than alone,
 * because the attribution usually lives in the words either side of it ("said
 * the minister", "according to Kaspersky"). Shown alone the question would be
 * unanswerable and the labeller would be guessing.
 */

import type { ReactNode } from "react";

import { HowToDecide } from "@/components/label/GuideView";
import { AnswerButtons, QuoteInContext, TaskFrame, type Answer } from "@/components/label/parts";
import type { LabelClaim, LabelGuide } from "@/lib/api";
import { KIND_QUESTION } from "@/lib/labeller";

export function ClaimTask({
  claim, position, tag, saving, pending, decide, feedback, onAnswer,
}: {
  claim: LabelClaim;
  position: number;
  tag?: string;
  saving: boolean;
  pending?: Answer | null;
  decide?: LabelGuide["decide"];
  feedback?: ReactNode;
  onAnswer: (answer: Answer) => void;
}) {
  const material = (
    <>
      <div className="grid gap-1">
        <h2 style={{ font: "var(--t-title)", textWrap: "pretty", overflowWrap: "anywhere" }}>{claim.title}</h2>
        <p className="p-count" style={{ whiteSpace: "normal" }}>{claim.source}</p>
      </div>

      <p style={{ font: "600 16px/1.45 var(--font-read)" }}>
        Does this article attribute the highlighted words to{" "}
        <strong style={{ borderBottom: "2px solid var(--ink)" }}>{claim.speaker}</strong>?
      </p>

      {claim.lead ? (
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)", overflowWrap: "anywhere" }}>
          <span className="font-semibold" style={{ color: "var(--ink-2)" }}>How the article opens · </span>
          {claim.lead}…
        </p>
      ) : null}

      <QuoteInContext before={claim.context_before} quote={claim.quote_text} after={claim.context_after} />

      {claim.article_text ? (
        <details>
          <summary className="flex min-h-11 cursor-pointer list-none items-center text-[14px] font-semibold [&::-webkit-details-marker]:hidden" style={{ color: "var(--accent)" }}>
            Read the whole article
          </summary>
          <p className="max-h-[420px] overflow-y-auto whitespace-pre-line" style={{ font: "var(--t-body-s)", color: "var(--ink-2)", overflowWrap: "anywhere" }}>
            {claim.article_text}
          </p>
        </details>
      ) : null}
    </>
  );
  return (
    <TaskFrame
      question={KIND_QUESTION.claim_attribution}
      tag={tag}
      material={material}
      panel={
        feedback ?? (
          <AnswerButtons
            yes={`Yes — ${claim.speaker.slice(0, 24)} said it`}
            no="No — someone else, or nobody"
            cantRead="Can't read this"
            saving={saving}
            picked={pending}
            onAnswer={onAnswer}
          />
        )
      }
      // Open on the FIRST question only. A claims labeller arrives with an
      // invite token, which skips the landing screen where the story flow
      // shows its guide open — so collapsed here meant the guide was never put
      // in front of anyone. The point of it is being read BEFORE the first
      // judgement, not after a wrong one.
      how={decide && <HowToDecide blocks={decide.blocks} closing={decide.closing} open={position === 0} />}
    />
  );
}
