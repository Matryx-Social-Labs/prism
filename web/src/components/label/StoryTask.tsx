"use client";

/**
 * The candidate task — story boundary, same happening, same topic: one anchor
 * report and the reports proposed beside it; tick every one that belongs.
 * Design System v2 · Label board, "Work · the five task kinds": the question as
 * the eyebrow, the anchor card under the ink rule, the instruction, candidate
 * rows (keys 1–n), and the answers — at the thumb on a phone, beside the
 * material on desktop with the keys that work, "How to decide" under them.
 *
 * Selection is the row's ink border and filled box, never a colour — colour is
 * the accent's, and a ticked row is not an action. Mono is provenance only:
 * dates, outlet counts, and which proposer suggested a row.
 */

import type { ReactNode } from "react";

import { AnswerButtons, CandidateRow, TaskFrame, type Answer } from "@/components/label/parts";
import { HowToDecide } from "@/components/label/GuideView";
import type { LabelEvent, LabelGuide, LabelTask } from "@/lib/api";
import { langName, langNative } from "@/lib/languages";
import { KIND_QUESTION } from "@/lib/labeller";

function provenance(e: LabelEvent): string {
  const bits = [
    // IST, the product's one clock: in the same-happening task the day a report
    // appeared is on the screen, and a browser elsewhere would move it.
    e.at ? new Date(e.at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", timeZone: "Asia/Kolkata" }) : "—",
    `${e.source_count} ${e.source_count === 1 ? "outlet" : "outlets"}`,
  ];
  if (e.actors.length) bits.push(e.actors.slice(0, 3).join(", "));
  return bits.join(" · ");
}

/** Which proposer suggested a row — provenance, never a score: a number on the
 *  row would anchor the judgement this set exists to collect. */
const proposers = (e: LabelEvent) => [...new Set(e.signals.map((s) => s.split(":")[0]))];

export function StoryTask({
  task, kind, tag, picked, saving, pending, decide, feedback, onToggle, onAnswer,
}: {
  task: LabelTask;
  kind?: string;
  tag?: string;
  picked: Set<string>;
  saving: boolean;
  pending?: Answer | null;
  decide?: LabelGuide["decide"];
  /** A practice answer's verdict, shown where the answers were. */
  feedback?: ReactNode;
  onToggle: (id: string) => void;
  onAnswer: (answer: Answer) => void;
}) {
  // The same-happening task (article -> event) is narrower than the story task:
  // the copy on screen says so at every step.
  const sameEvent = kind === "event_identity";
  const sameTopic = kind === "topic_relation";
  const candidates = task.candidates ?? [];
  const seed = task.seed;
  const native = sameEvent && seed?.native_title && seed.native_title !== seed.title ? seed : null;
  // The one line on screen that may not be English is the founding outlet's own
  // headline; say which language it is when it is not.
  const foreign = native?.language && native.language !== "en" ? native.language : null;

  const material = (
    <>
      {seed && (
        <div className="p-card grid gap-1.5" style={{ borderTop: "var(--rule-section) solid var(--ink)" }}>
          <h2 style={{ font: "var(--t-title)", textWrap: "pretty", overflowWrap: "anywhere" }}>{seed.title}</h2>
          {native && (
            <p lang={native.language || undefined} style={{ font: "600 16px/1.45 var(--font-record)", color: "var(--ink-2)", overflowWrap: "anywhere" }}>
              {native.native_title}{" "}
              {foreign && <span className="p-count">{langNative(foreign)} · as filed</span>}
            </p>
          )}
          <p className="p-count" style={{ whiteSpace: "normal" }}>{provenance(seed)}</p>
        </div>
      )}

      <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
        {sameEvent
          ? "Which of these report the same happening — the same incident, whatever day it was reported?"
          : sameTopic
            ? "Which of these are genuinely useful context about the same issue?"
            : "Which of these are part of the same unfolding story?"}
      </p>

      {candidates.length > 0 && (
        <ul className="p-print grid gap-2">
          {candidates.map((c, i) => (
            <li key={c.id}>
              <CandidateRow
                n={i + 1}
                headline={c.title}
                meta={provenance(c)}
                signals={proposers(c)}
                selected={picked.has(c.id)}
                disabled={!!feedback}
                onToggle={() => onToggle(c.id)}
              />
            </li>
          ))}
        </ul>
      )}

      <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
        {sameEvent ? (
          <>The follow-up is a different happening here; a different incident of the same kind is too. <strong>Not sure</strong> is a real answer.</>
        ) : sameTopic ? (
          <>These are already different stories. Tick only useful context about the same issue; a shared name, place, or sector is not enough.</>
        ) : (
          <>Same topic isn&apos;t enough — two different court cases about one law are two
          stories. <strong>Not sure</strong> is a real answer; it keeps genuinely hard
          calls out of the training data rather than guessing at them.</>
        )}
      </p>
    </>
  );

  return (
    <TaskFrame
      question={KIND_QUESTION[kind ?? "story_boundary"] ?? KIND_QUESTION.story_boundary}
      tag={tag}
      material={material}
      panel={
        feedback ?? (
          <AnswerButtons
            yes={sameTopic ? "Related" : "Yes"}
            count={picked.size}
            no="None of these"
            // Distinct from "Not sure" on purpose. "Not sure" says the STORY is
            // ambiguous and is read as a signal about the boundary; this says the
            // READER cannot assess it, and routes the task to someone else.
            cantRead={foreign ? `I can't read ${langName(foreign)}` : "Can't read this"}
            saving={saving}
            picked={pending}
            // Enter is the one answer key with a handler (the page's 1–n and Enter).
            keys={{ yes: "Enter" }}
            onAnswer={onAnswer}
          />
        )
      }
      keys={
        !feedback && candidates.length > 0 ? (
          <>
            <kbd className="p-kbd">1</kbd>–<kbd className="p-kbd">{candidates.length}</kbd> toggle ·{" "}
            <kbd className="p-kbd">Enter</kbd> submits
          </>
        ) : undefined
      }
      // An INVITED labeller never sees the join screen, so this is the only
      // route the worked example has to them. Collapsed, because it is
      // reference rather than instruction once you are going.
      how={decide && <HowToDecide blocks={decide.blocks} closing={decide.closing} />}
    />
  );
}
