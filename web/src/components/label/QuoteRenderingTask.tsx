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
 * the labeller, never a vote about the quote.
 */

import type { LabelRendering, LabelRenderedQuote } from "@/lib/api";

function Quote({ q }: { q: LabelRenderedQuote }) {
  return (
    <figure className="mt-4 border-l-2 pl-4" style={{ borderColor: "var(--ink)" }}>
      <blockquote className="font-record text-[18px] italic leading-[1.55]" lang={q.code || undefined}>
        “{q.quote}”
      </blockquote>
      <figcaption className="mt-1.5 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
        {q.language.toUpperCase()} · {q.outlet}
      </figcaption>
    </figure>
  );
}

export function QuoteRenderingTask({
  rendering, position, saving, onAnswer,
}: {
  rendering: LabelRendering;
  position: number;
  saving: boolean;
  onAnswer: (verdict: "yes" | "no" | "unsure" | "skip") => void;
}) {
  const same = rendering.question === "same";
  const heading = same
    ? `Is this the same statement by ${rendering.speaker}?`
    : `Did ${rendering.speaker} say this in ${rendering.a.language}?`;
  const unreadable = [rendering.a, rendering.b].filter(Boolean).map((q) => q!.language).filter((l) => l !== "English");
  return (
    <div>
      <p className="font-mono text-[11px] uppercase" style={{ color: "var(--ink-faint)" }}>
        question {position + 1}
      </p>
      <h1 className="mt-2 text-[23px] leading-[1.3]" style={{ fontFamily: "var(--font-display), serif", textWrap: "pretty" }}>
        {heading}
      </h1>
      <p className="mt-2 text-[14px]" style={{ color: "var(--ink-muted)" }}>{rendering.story}</p>
      <Quote q={rendering.a} />
      {rendering.b && <Quote q={rendering.b} />}
      <p className="mt-5 text-[14px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
        {same
          ? "Yes if both report the same thing said — a translation reads differently and still counts. No if they are two different things said."
          : `No if ${rendering.a.outlet} translated it from the language ${rendering.speaker} actually spoke. You are not judging whether it is true.`}
      </p>
      {/* The claim task's answer row, as it is: one ink pill for yes, rules for the rest. */}
      <div className="mt-6 flex flex-wrap items-center gap-3 border-t pt-5" style={{ borderColor: "var(--line)" }}>
        <button
          type="button" disabled={saving} onClick={() => onAnswer("yes")}
          className="h-11 rounded-full px-5 text-[14.5px] font-medium disabled:opacity-50"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          {same ? "Yes — the same statement" : `Yes — said in ${rendering.a.language}`}
        </button>
        <button
          type="button" disabled={saving} onClick={() => onAnswer("no")}
          className="h-11 rounded-full border px-5 text-[14.5px] disabled:opacity-50"
          style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}
        >
          {same ? "No — two different statements" : "No — the outlet translated it"}
        </button>
        <button
          type="button" disabled={saving} onClick={() => onAnswer("unsure")}
          className="h-11 rounded-full border px-5 text-[14.5px] disabled:opacity-50"
          style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
        >
          Not sure
        </button>
        {unreadable.length > 0 && (
          <button
            type="button" disabled={saving} onClick={() => onAnswer("skip")}
            className="h-11 rounded-full border px-5 text-[14.5px] disabled:opacity-50"
            style={{ borderColor: "var(--line)", color: "var(--ink-faint)" }}
          >
            I can&apos;t read {[...new Set(unreadable)].join(" or ")}
          </button>
        )}
      </div>
    </div>
  );
}
