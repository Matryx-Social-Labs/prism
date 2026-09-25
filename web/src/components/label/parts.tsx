"use client";

/**
 * The labeller's building blocks (Design System v2 · label/*): the strip, the
 * task header, a candidate row, the answer footer, a verdict and a quote in its
 * sentence. Selection and verdicts are carried by rule weight, a filled mark
 * and a word — never by colour alone (the Legend Rule).
 */

import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";

import { Brand } from "@/components/Brand";
import { Check, Close, Dash } from "@/components/icons";

/** The highlight on the words a question is about. */
export const MARK: CSSProperties = {
  background: "var(--accent-soft)",
  color: "var(--ink)",
  boxShadow: "inset 0 -2px 0 var(--accent)",
  padding: "0 2px",
  borderRadius: 2,
};

/** The brand, and which corner of Prism this is. Phone only: /label hides the
 *  site header there, and on desktop the header already carries the brand. */
export function LabelStrip() {
  return (
    <div className="flex items-center gap-2.5 lg:hidden">
      <Brand size={22} />
      <span className="p-count ml-auto">LABEL FOR PRISM</span>
    </div>
  );
}

/** Sticky over the task: the way back, the batch, and this labeller's own count.
 *  Below the desktop top bar, which is sticky too; on the phone /label has none. */
export function TaskHeader({ batch, done, total }: { batch: string; done?: number; total?: number }) {
  const counted = done != null && total != null;
  const pct = counted && total ? Math.min(100, (done / total) * 100) : 0;
  return (
    <header
      className="sticky top-0 z-20 border-b lg:top-[var(--topbar)]"
      style={{ background: "var(--paper)", borderColor: "var(--line)" }}
    >
      <div className="flex min-h-[52px] items-center gap-2.5 pl-4 pr-3">
        <Link
          href="/label"
          className="inline-flex min-h-11 shrink-0 items-center text-[14px] font-semibold"
          style={{ color: "var(--ink-2)" }}
        >
          ← Workspace
        </Link>
        <span className="min-w-0 flex-1 truncate text-center text-[14px] font-semibold">{batch}</span>
        <span aria-hidden className="p-mono shrink-0 text-[12.5px]">
          {counted ? `${String(done).padStart(3, "0")} / ${total}` : "—"}
        </span>
        {counted && <span className="sr-only">{done} of {total} done</span>}
      </div>
      <div aria-hidden className="h-[2px]" style={{ background: "var(--line)" }}>
        <div
          className="h-[2px] motion-reduce:transition-none"
          style={{ width: `${pct}%`, background: "var(--ink)", transition: "width var(--t-std) var(--ease)" }}
        />
      </div>
    </header>
  );
}

/** One report to tick. Selected is a 2px ink border and a filled box — the
 *  padding gives back the extra pixel so nothing shifts. */
export function CandidateRow({
  n, headline, meta, signals, selected, onToggle,
}: {
  n: number;
  headline: string;
  meta: string;
  signals: string[];
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      data-candidate
      onClick={onToggle}
      aria-pressed={selected}
      className="grid min-h-16 w-full grid-cols-[28px_minmax(0,1fr)_24px] gap-3 text-left"
      style={{
        padding: selected ? 13 : 14,
        border: selected ? "2px solid var(--ink)" : "1px solid var(--line-strong)",
        borderRadius: "var(--r-md)",
        background: selected ? "var(--surface)" : "var(--paper)",
      }}
    >
      <span
        aria-hidden
        className="grid h-6 w-6 place-items-center"
        style={{
          borderRadius: "var(--r-sm)",
          border: `1.5px solid ${selected ? "var(--ink)" : "var(--line-strong)"}`,
          background: selected ? "var(--ink)" : "transparent",
          color: "var(--paper)",
        }}
      >
        {selected && <Check size={16} />}
      </span>
      <span className="grid min-w-0 gap-1">
        <span className="font-record text-[16px] font-semibold leading-[1.4]" style={{ overflowWrap: "anywhere" }}>
          {headline}
        </span>
        <span className="p-count" style={{ whiteSpace: "normal" }}>{meta}</span>
        {signals.length > 0 && (
          <span className="flex flex-wrap gap-1">
            {signals.map((s) => (
              <span key={s} className="p-badge p-badge--outline" style={{ fontSize: 11 }}>{s}</span>
            ))}
          </span>
        )}
      </span>
      <span aria-hidden className="p-mono text-right text-[12px]" style={{ color: "var(--ink-3)" }}>{n}</span>
    </button>
  );
}

const WRAP: CSSProperties = { whiteSpace: "normal", textAlign: "center" };

/** The answer footer, sticky at the bottom of the task: yes, no, and the two
 *  answers that are not a vote on the question. "Not sure" says the question
 *  is ambiguous; "can't read" says the labeller cannot assess it (a skip). */
export function AnswerButtons({
  yes, no, cantRead, saving, yesDisabled, onYes, onNo, onUnsure, onCantRead,
}: {
  yes: string;
  no: string;
  cantRead?: string;
  saving: boolean;
  yesDisabled?: boolean;
  onYes: () => void;
  onNo: () => void;
  onUnsure: () => void;
  onCantRead: () => void;
}) {
  return (
    <div
      className="sticky bottom-0 z-10 -mx-4 mt-auto grid gap-2 border-t px-4 pt-3"
      style={{ background: "var(--paper)", borderColor: "var(--line)", paddingBottom: "calc(16px + env(safe-area-inset-bottom))" }}
    >
      <button
        type="button" className="p-btn p-btn--primary p-btn--lg p-btn--block" style={WRAP}
        disabled={saving || yesDisabled} aria-busy={saving || undefined} onClick={onYes}
      >
        {saving ? "Saving…" : yes}
      </button>
      <button type="button" className="p-btn p-btn--secondary p-btn--lg p-btn--block" style={WRAP} disabled={saving} onClick={onNo}>
        {no}
      </button>
      <div className={cantRead ? "grid grid-cols-2 gap-2" : "grid"}>
        <button type="button" className="p-btn p-btn--ghost" style={WRAP} disabled={saving} onClick={onUnsure}>
          Not sure
        </button>
        {cantRead && (
          <button type="button" className="p-btn p-btn--ghost" style={WRAP} disabled={saving} onClick={onCantRead}>
            {cantRead}
          </button>
        )}
      </div>
    </div>
  );
}

export type VerdictKind = "right" | "wrong" | "neutral";

/** A guide's yes/no mark as a verdict kind. */
export const markKind = (mark?: "yes" | "no"): VerdictKind => (mark === "yes" ? "right" : mark === "no" ? "wrong" : "neutral");

const VERDICT = {
  right: { rule: "2px solid var(--ink)", Icon: Check },
  wrong: { rule: "2px dashed var(--ink)", Icon: Close },
  neutral: { rule: "1px solid var(--line-strong)", Icon: Dash },
} as const;

/** A word and its icon on a rule: solid for right, dashed for wrong, hairline
 *  otherwise. The word always carries it; the icon and the rule repeat it. */
export function Verdict({ word, kind = "neutral", children }: { word?: ReactNode; kind?: VerdictKind; children?: ReactNode }) {
  const { rule, Icon } = VERDICT[kind];
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1.5 py-3.5" style={{ borderTop: rule }}>
      <span className="inline-flex items-start gap-1.5 text-[12px] font-semibold uppercase leading-[1.35] tracking-[0.06em]">
        <span aria-hidden className="inline-flex shrink-0"><Icon size={16} /></span>
        {word}
      </span>
      <div className="grid min-w-0 flex-[1_1_16rem] gap-1.5" style={{ font: "var(--t-body-s)" }}>{children}</div>
    </div>
  );
}

/** A quote as the reader meets it: inside its own sentence with the words in
 *  question marked, or on its own. Context is joined exactly as the article
 *  has it — no space is added, since that would change a verbatim quote. */
export function QuoteInContext({
  quote, before, after, code, caption = [],
}: {
  quote: string;
  before?: string;
  after?: string;
  code?: string;
  caption?: string[];
}) {
  const inContext = before != null || after != null;
  return (
    <figure className="grid gap-2">
      <blockquote lang={code || undefined}>
        {inContext ? (
          <p style={{ font: "400 16px/1.7 var(--font-read)", color: "var(--ink-2)" }}>
            …{before}<mark style={MARK}>{quote}</mark>{after}…
          </p>
        ) : (
          <p style={{ font: "var(--t-quote)", color: "var(--ink)" }}>“{quote}”</p>
        )}
      </blockquote>
      {caption.length > 0 && (
        <figcaption className="flex flex-wrap items-center gap-2 text-[12.5px] font-medium" style={{ color: "var(--ink-3)" }}>
          {caption.map((c, i) => (
            <span key={i} className="contents">
              {i > 0 && <span className="p-meta__sep" />}
              <span>{c}</span>
            </span>
          ))}
        </figcaption>
      )}
    </figure>
  );
}
