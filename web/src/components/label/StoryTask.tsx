"use client";

/**
 * The candidate task — story boundary, same happening, same topic: one anchor
 * report and the reports proposed beside it; tick every one that belongs.
 * Design System v2 · labeller Task: the question as the eyebrow, the anchor
 * card, the instruction, candidate rows (keys 1–n), "How to decide" from the
 * guide this batch's invite was served, the key hint, the sticky answer footer.
 *
 * Selection is the row's ink border and filled box, never a colour — colour is
 * the accent's, and a ticked row is not an action. Mono is provenance only:
 * dates, outlet counts, and which proposer suggested a row.
 */

import { AnswerButtons, CandidateRow } from "@/components/label/parts";
import { HowToDecide } from "@/components/label/GuideView";
import type { LabelEvent, LabelGuide, LabelTask } from "@/lib/api";
import { KIND_QUESTION } from "@/lib/labeller";

export type StoryAnswer = "picked" | "none" | "unsure" | "skip";

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
  task, kind, picked, saving, decide, onToggle, onAnswer,
}: {
  task: LabelTask;
  kind?: string;
  picked: Set<string>;
  saving: boolean;
  decide?: LabelGuide["decide"];
  onToggle: (id: string) => void;
  onAnswer: (answer: StoryAnswer) => void;
}) {
  // The same-happening task (article -> event) is narrower than the story task:
  // the copy on screen says so at every step.
  const sameEvent = kind === "event_identity";
  const sameTopic = kind === "topic_relation";
  const candidates = task.candidates ?? [];
  const seed = task.seed;
  return (
    <>
      <h1 className="p-eyebrow">{KIND_QUESTION[kind ?? "story_boundary"] ?? KIND_QUESTION.story_boundary}</h1>
      {seed && (
        <div className="p-card grid gap-1.5">
          <h2 style={{ font: "var(--t-title)", textWrap: "pretty", overflowWrap: "anywhere" }}>{seed.title}</h2>
          {sameEvent && seed.native_title && seed.native_title !== seed.title && (
            <p style={{ font: "var(--t-body)", color: "var(--ink)" }} lang={seed.language || undefined}>
              {seed.native_title}
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

      {/* An INVITED labeller never sees the join screen, so this is the only
          route the worked example has to them. Collapsed, because it is
          reference rather than instruction once you are going. */}
      {decide && <HowToDecide blocks={decide.blocks} closing={decide.closing} />}

      {candidates.length > 0 && (
        <p className="p-count" style={{ whiteSpace: "normal" }}>
          Desktop: <kbd className="p-kbd">1</kbd>–<kbd className="p-kbd">{candidates.length}</kbd> toggle ·{" "}
          <kbd className="p-kbd">Enter</kbd> submits
        </p>
      )}

      <AnswerButtons
        yes={`${sameTopic ? "Related" : "Yes"} — ${picked.size} selected`}
        yesDisabled={picked.size === 0}
        no="None of these"
        // Distinct from "Not sure" on purpose. "Not sure" says the STORY is
        // ambiguous and is read as a signal about the boundary; this says the
        // READER cannot assess it, and routes the task to someone else.
        cantRead="Can't read this"
        saving={saving}
        onYes={() => onAnswer("picked")}
        onNo={() => onAnswer("none")}
        onUnsure={() => onAnswer("unsure")}
        onCantRead={() => onAnswer("skip")}
      />
    </>
  );
}
