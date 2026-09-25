"use client";

/**
 * The labeller's building blocks (Design System v2 · label/* and the Label flow
 * board): the strip, the column, the task header, the task frame, a candidate
 * row, the answers, a verdict, a quote in its sentence and an end screen.
 * Selection and verdicts are carried by rule weight, a filled mark and a word —
 * never by colour alone (the Legend Rule).
 */

import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";

import { Brand } from "@/components/Brand";
import { ArrowLeft, Check, Close, Dash, InfoIcon } from "@/components/icons";

/** The highlight on the words a question is about. */
export const MARK: CSSProperties = {
  background: "var(--accent-soft)",
  color: "var(--ink)",
  boxShadow: "inset 0 -2px 0 var(--accent)",
  padding: "0 2px",
  borderRadius: 2,
};

/** The label bar: the brand, which corner of Prism this is, and whose account.
 *  Phone only: on desktop the site's top bar is over /label. */
export function LabelStrip({ email }: { email?: string | null }) {
  return (
    <header
      className="flex h-[52px] shrink-0 items-center gap-2.5 border-b px-[var(--gutter)] lg:h-[var(--topbar)]"
      style={{ borderColor: "var(--line)", background: "var(--paper)" }}
    >
      <Brand size={20} />
      <span className="p-badge p-badge--outline">Label</span>
      <span className="flex-1" />
      {email && <span className="p-count min-w-0 truncate">{email}</span>}
    </header>
  );
}

/** The label pages' column: one measure, the board's rhythm. */
export function Column({ children, wide = false, className = "" }: { children: ReactNode; wide?: boolean; className?: string }) {
  return (
    <div className={`mx-auto grid w-full min-w-0 content-start px-[var(--gutter)] pb-8 pt-5 lg:pb-14 lg:pt-11 ${wide ? "max-w-[760px] gap-[30px]" : "max-w-[640px] gap-6"} ${className}`}>
      {children}
    </div>
  );
}

/** A title in the record voice, one size down on the phone. */
export function Title({ children, as: Tag = "h1", big = false }: { children: ReactNode; as?: "h1" | "h2"; big?: boolean }) {
  return (
    <Tag
      className={big ? "[font:var(--t-display-l)] lg:[font:var(--t-display-xl)]" : "[font:var(--t-display-m)] lg:[font:var(--t-display-l)]"}
      style={{ letterSpacing: "var(--track-display)", textWrap: "balance", overflowWrap: "anywhere" }}
    >
      {children}
    </Tag>
  );
}

export function Lede({ children }: { children: ReactNode }) {
  return <p className="max-w-[60ch]" style={{ font: "var(--t-body)", color: "var(--ink-2)", textWrap: "pretty" }}>{children}</p>;
}

export function Small({ children }: { children: ReactNode }) {
  return <p style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)", textWrap: "pretty" }}>{children}</p>;
}

/** "Back to your workspace", the one way out of every label screen. */
export function BackToWorkspace() {
  return (
    <Link href="/label" className="p-link inline-flex min-h-11 items-center gap-1.5 justify-self-start text-[14.5px] font-semibold">
      <ArrowLeft size={16} />
      Back to your workspace
    </Link>
  );
}

/** Sticky over the task: the way back, the batch, and which question this is. */
export function TaskHeader({ batch, done, total }: { batch: string; done?: number; total?: number }) {
  const counted = done != null && total != null && total > 0;
  const n = counted ? Math.min(done + 1, total) : 0;
  const pct = counted ? Math.min(100, (done / total) * 100) : 0;
  return (
    <header
      className="sticky top-0 z-20 border-b lg:top-[var(--topbar)]"
      style={{ background: "var(--paper)", borderColor: "var(--line)" }}
    >
      <div className="mx-auto flex min-h-[52px] max-w-[1128px] items-center gap-2.5 pl-4 pr-3 lg:px-6">
        <Link
          href="/label"
          className="inline-flex min-h-11 shrink-0 items-center gap-1.5 text-[14px] font-semibold"
          style={{ color: "var(--ink-2)" }}
        >
          <ArrowLeft size={16} />
          Workspace
        </Link>
        <span className="min-w-0 flex-1 truncate text-center text-[14px] font-semibold">{batch}</span>
        <span aria-hidden className="p-mono shrink-0 text-[12.5px]">
          {counted ? `${String(n).padStart(3, "0")} / ${total}` : "—"}
        </span>
        {counted && <span className="sr-only">Question {n} of {total}</span>}
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

/**
 * One decision per screen. On the phone the answers sit in a bar at the thumb,
 * with "How to decide" above them; on desktop they sit beside the material with
 * their keys, and "How to decide" under them. One copy of each in the DOM: the
 * side column is `display: contents` on the phone and its parts are re-ordered.
 */
export function TaskFrame({
  question, tag, material, panel, keys, how,
}: {
  question: ReactNode;
  tag?: string;
  material: ReactNode;
  /** The answers, or a practice answer's verdict in their place. */
  panel: ReactNode;
  keys?: ReactNode;
  how?: ReactNode;
}) {
  return (
    <div className="flex flex-1 flex-col gap-4 px-4 pt-4 lg:mx-auto lg:grid lg:w-full lg:max-w-[1128px] lg:grid-cols-[minmax(0,680px)_360px] lg:content-start lg:justify-center lg:gap-x-10 lg:gap-y-0 lg:px-6 lg:pb-12 lg:pt-7">
      <div className="grid min-w-0 content-start gap-4">
        <div className="flex flex-wrap items-center gap-2">
          {tag && <span className={`p-badge ${tag === "Test" ? "p-badge--ink" : "p-badge--outline"}`}>{tag}</span>}
          <h1 className="p-eyebrow">{question}</h1>
        </div>
        {material}
      </div>
      <div className="contents lg:sticky lg:top-[calc(var(--topbar)+72px)] lg:grid lg:min-w-0 lg:content-start lg:gap-3.5 lg:self-start">
        <div
          className="sticky bottom-0 z-10 order-2 -mx-4 mt-auto max-h-[75dvh] overflow-y-auto border-t px-4 pt-3 lg:static lg:order-none lg:m-0 lg:max-h-none lg:overflow-visible lg:border-0 lg:p-0"
          style={{ background: "var(--paper)", borderColor: "var(--line)", paddingBottom: "calc(14px + env(safe-area-inset-bottom))" }}
        >
          {panel}
        </div>
        {keys && (
          <p className="p-count hidden flex-wrap items-center gap-1.5 lg:flex" style={{ whiteSpace: "normal" }}>
            {keys}
          </p>
        )}
        {how && <div className="order-1 min-w-0 lg:order-none">{how}</div>}
      </div>
    </div>
  );
}

/** One report to tick. Selected is a 2px ink border and a filled box — the
 *  padding gives back the extra pixel so nothing shifts. */
export function CandidateRow({
  n, headline, meta, signals, selected, disabled, onToggle,
}: {
  n: number;
  headline: string;
  meta: string;
  signals: string[];
  selected: boolean;
  disabled?: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      data-candidate
      onClick={onToggle}
      disabled={disabled}
      aria-pressed={selected}
      className="grid min-h-16 w-full grid-cols-[28px_minmax(0,1fr)_24px] gap-3 text-left disabled:cursor-default"
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

export type Answer = "yes" | "no" | "unsure" | "cant";

const ICON: Record<Answer, ReactNode> = {
  yes: <Check size={18} />,
  no: <Close size={18} />,
  unsure: <InfoIcon size={18} />,
  cant: <Dash size={18} />,
};

function Key({ k }: { k?: string }) {
  if (!k) return null;
  return (
    <kbd
      aria-hidden
      className="ml-auto hidden h-[22px] min-w-[22px] shrink-0 items-center justify-center px-1.5 lg:inline-flex"
      style={{ border: "1px solid currentColor", borderRadius: 4, font: "500 11px/1 var(--font-mono)", opacity: 0.8 }}
    >
      {k}
    </kbd>
  );
}

/**
 * Yes, no, and the two answers that are not a vote on the question: "Not sure"
 * says the question is ambiguous; "can't read" says the labeller cannot assess
 * it (a skip). Every answer is a word with an icon. On a tick task Yes carries
 * the count and waits for one; the answer being saved is outlined and says so.
 */
export function AnswerButtons({
  yes, no, cantRead, saving, count, picked, keys = {}, onAnswer,
}: {
  yes: string;
  no: string;
  cantRead?: string;
  saving: boolean;
  count?: number;
  picked?: Answer | null;
  /** Key hints, desktop only — and only for keys that have a handler. */
  keys?: Partial<Record<Answer, string>>;
  onAnswer: (answer: Answer) => void;
}) {
  const needsPick = count === 0;
  const label = (a: Answer, text: string) => (saving && picked === a ? "Saving…" : text);
  const button = (a: Answer, cls: string, text: string, disabled = false) => (
    <button
      type="button"
      className={`p-btn ${cls} justify-start gap-2.5 text-left leading-[1.25]`}
      style={{
        whiteSpace: "normal",
        outline: picked === a ? "2px solid var(--ink)" : undefined,
        outlineOffset: picked === a ? 2 : undefined,
      }}
      disabled={saving || disabled}
      aria-busy={(saving && picked === a) || undefined}
      onClick={() => onAnswer(a)}
    >
      <span aria-hidden className="inline-flex shrink-0">{ICON[a]}</span>
      <span className="min-w-0">{label(a, text)}</span>
      {/* A key hint only where the key would act: not on a Yes that waits for a tick. */}
      <Key k={disabled ? undefined : keys[a]} />
    </button>
  );
  const yesText = needsPick ? "Tick one, or choose None" : count != null ? `${yes} — ${count} selected` : yes;
  return (
    <div className="grid gap-2" role="group" aria-label="Your answer">
      {button("yes", "p-btn--primary p-btn--lg p-btn--block", yesText, needsPick)}
      {button("no", "p-btn--secondary p-btn--lg p-btn--block", no)}
      <div className={cantRead ? "grid grid-cols-2 gap-2" : "grid"}>
        {button("unsure", "p-btn--ghost min-h-12", "Not sure")}
        {cantRead && button("cant", "p-btn--ghost min-h-12", cantRead)}
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
 *  question marked. Context is joined exactly as the article has it — no space
 *  is added, since that would change a verbatim quote. */
export function QuoteInContext({ quote, before, after }: { quote: string; before?: string; after?: string }) {
  return (
    <figure className="grid gap-2">
      <blockquote>
        <p style={{ font: "400 16px/1.7 var(--font-read)", color: "var(--ink-2)", overflowWrap: "anywhere" }}>
          …{before}<mark style={MARK}>{quote}</mark>{after}…
        </p>
      </blockquote>
    </figure>
  );
}

/** The end of something: a title on the section rule (dashed when it did not
 *  go well), what it means, and the way back. */
export function EndScreen({
  title, children, dashed = false, action,
}: {
  title: ReactNode;
  children?: ReactNode;
  dashed?: boolean;
  action?: ReactNode;
}) {
  return (
    <section className="grid gap-4">
      <div className="grid gap-3 pt-[18px]" style={{ borderTop: `var(--rule-section) ${dashed ? "dashed" : "solid"} var(--ink)` }}>
        <Title>{title}</Title>
        {children}
      </div>
      {action !== undefined ? action : (
        <div>
          <Link href="/label" className="p-btn p-btn--primary p-btn--lg w-full lg:w-auto">Back to your workspace</Link>
        </div>
      )}
    </section>
  );
}
