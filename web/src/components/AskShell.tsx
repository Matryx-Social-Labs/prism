"use client";

import Link from "next/link";
import { ArrowUp, Close } from "@/components/icons";
import type { AskCitation, AskLimit, AskStructure } from "@/lib/api";
import type { KeyboardEvent, RefObject } from "react";

// The Ask panel's body, one markup for the ticket's live panel and the
// landing's scripted one: header, the exchange (Q and A lines on rules, a
// refusal as a first-class state, citations in mono), suggestions, input.

export interface Turn {
  role: "u" | "a";
  text: string;
  citations: AskCitation[];
  error?: string;
  /** The server refused before answering; what would help is in here. */
  limit?: AskLimit;
  /** After the prose: a table, the honesty line, follow-ups. */
  structure?: AskStructure;
  streaming: boolean;
}

/** The answer's anatomy after the prose: table · what the reports don't say. (Its follow-ups take the suggestion row.) */
export function AnswerStructure({ s, citations }: { s: AskStructure; citations: AskCitation[] }) {
  const [left, right] = s.columns.length === 2 ? s.columns : ["", ""];
  return (
    <div className="mt-3 flex flex-col gap-3">
      {s.rows.length > 0 && (
        <table className="w-full border-collapse text-[13px] leading-[1.5]" aria-label={s.kind ?? "table"}>
          {(left || right) && (
            <thead>
              <tr className="text-left text-[11.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>
                <th scope="col" className="border-b py-1.5 pr-3 font-semibold" style={{ borderColor: "var(--line-strong)" }}>{left}</th>
                <th scope="col" className="border-b py-1.5 font-semibold" style={{ borderColor: "var(--line-strong)" }}>{right}</th>
              </tr>
            </thead>
          )}
          <tbody>
            {s.rows.map((r, i) => (
              <tr key={i} className="align-top">
                <td className={`border-b py-2 pr-3 ${s.kind === "who_said" ? "font-semibold" : ""} ${s.kind === "timeline" || s.kind === "numbers" ? "whitespace-nowrap font-mono text-[12px]" : ""}`} style={{ borderColor: "var(--line)", color: "var(--ink)" }}>{r.a}</td>
                <td className={`border-b py-2 ${s.kind === "who_said" ? "font-record italic" : ""}`} style={{ borderColor: "var(--line)", color: "var(--ink)" }}>
                  {s.kind === "who_said" ? <>“{r.b}”</> : r.b} {r.n && <AnswerText text={r.n} citations={citations} />}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {s.gaps && (
        <p className="text-[13px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
          <span className="mr-2 font-mono text-[11px]" style={{ color: "var(--ink)" }}>Not in the reports</span>
          {s.gaps}
        </p>
      )}
    </div>
  );
}

/** The answer's `[n]` markers as mono chips that open the cited report. */
export function AnswerText({ text, citations }: { text: string; citations: AskCitation[] }) {
  // The prompt asks for plain text; a model that bolds anyway must not show asterisks.
  const parts = text.replace(/\*\*/g, "").split(/(\[\d+\])/g);
  return (
    <>
      {parts.map((part, i) => {
        const m = /^\[(\d+)\]$/.exec(part);
        if (!m) return <span key={i}>{part}</span>;
        const n = Number(m[1]);
        const c = citations.find((x) => x.number === n || x.numbers?.includes(n));
        const chip = "mx-px inline-block rounded-[4px] px-1 align-baseline font-mono text-[11px] leading-[1.6]";
        return c?.url ? (
          <a key={i} href={c.url} target="_blank" rel="noopener noreferrer" title={c.source_name} className={`${chip} underline-offset-2 hover:underline`} style={{ background: "var(--sunken)", color: "var(--ink)" }}>{part}</a>
        ) : (
          <span key={i} className={chip} style={{ background: "var(--sunken)", color: "var(--ink-2)" }}>{part}</span>
        );
      })}
    </>
  );
}

export type UpgradeAsk = { reason: "ask-limit" | "ask-rest"; used?: number; limit?: number };

/** What a refused question tells the reader, and the one action that helps. */
export function LimitNote({ limit, next, onUpgrade }: { limit: AskLimit; next: string; onUpgrade?: (o: UpgradeAsk) => void }) {
  const plusLink = (label: string, o: UpgradeAsk) =>
    onUpgrade ? (
      <button type="button" onClick={() => onUpgrade(o)} className="font-semibold underline underline-offset-4" style={{ color: "var(--accent)" }}>{label}</button>
    ) : (
      <Link href="/plus" className="font-semibold underline underline-offset-4" style={{ color: "var(--accent)" }}>{label}</Link>
    );
  if (limit.retry_after_s) return <p className="text-[13.5px] leading-[1.6]" style={{ color: "var(--ink)" }}>One question at a time — try again in a minute.</p>;
  if (limit.status === 503) {
    return (
      <p className="text-[13.5px] leading-[1.6]" style={{ color: "var(--ink)" }}>
        Ask is resting for today for free readers. It is back at midnight UTC.{" "}
        {limit.plus_helps && plusLink("Plus stays on →", { reason: "ask-rest" })}
      </p>
    );
  }
  if (limit.signin_helps) {
    return (
      <p className="text-[13.5px] leading-[1.6]" style={{ color: "var(--ink)" }}>
        That was your last free question here.{" "}
        <Link href={`/signin?next=${encodeURIComponent(next)}`} className="font-semibold underline underline-offset-4" style={{ color: "var(--accent)" }}>Sign in for 10 a day →</Link>
      </p>
    );
  }
  return (
    <p className="text-[13.5px] leading-[1.6]" style={{ color: "var(--ink)" }}>
      You have asked {limit.used ?? limit.limit} of {limit.limit} questions today.
      {limit.plus_helps && <> {plusLink("Plus is 100 a day →", { reason: "ask-limit", used: limit.used, limit: limit.limit })}</>}
    </p>
  );
}

/** The analyst's three, always available before the first question: each is
 * answered as a table (agent/structure.py kinds) rather than prose. */
export const DIG_DEEPER: { label: string; question: string }[] = [
  { label: "Timeline", question: "Give me a timeline of what changed in this story, with dates." },
  { label: "Every quote", question: "Give me every direct quote in the reports, with who said it." },
  { label: "How outlets differ", question: "Which outlets reported this, and what did only one of them report?" },
];

export function isRefusal(turn: Turn): boolean {
  return !turn.streaming && turn.citations.length === 0 && /don'?t cover|do not say|not in sources|refus/i.test(turn.text);
}

export function AskShell({
  sourceCount,
  turns,
  thinking = false,
  input,
  onInput,
  onSubmit,
  onFollowUp,
  onUpgrade,
  suggestions,
  onClose,
  inputRef,
  scrollRef,
  className = "",
  style,
}: {
  sourceCount: number;
  turns: Turn[];
  thinking?: boolean;
  input: string;
  onInput: (v: string) => void;
  onSubmit: (q: string) => void;
  /** A follow-up chip under an answer; absent on the landing's scripted panel. */
  onFollowUp?: (q: string) => void;
  /** Opens the upgrade sheet from a limit; absent where there is no account to upgrade. */
  onUpgrade?: (o: UpgradeAsk) => void;
  suggestions: string[];
  /** Absent on the landing's embedded panel, which has nothing to close. */
  onClose?: () => void;
  inputRef?: RefObject<HTMLInputElement | null>;
  scrollRef?: RefObject<HTMLDivElement | null>;
  className?: string;
  style?: React.CSSProperties;
}) {
  const last = turns[turns.length - 1];
  const chips = turns.length === 0 ? suggestions : last?.role === "a" && !last.streaming ? (last.structure?.followups ?? []) : [];
  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    // isComposing: for Devanagari/Tamil/Telugu IMEs, Enter confirms the
    // candidate. Submitting on it sends a half-composed question.
    if (e.key === "Enter" && !e.nativeEvent.isComposing) onSubmit(input);
  };
  return (
    <section
role="dialog"
aria-label="Ask this story"
className={`flex flex-col overflow-hidden ${className}`}
style={{ borderColor: "var(--line-strong)", background: "var(--bg-elevated)", ...style }}
    >
      <div className="flex items-baseline gap-3 border-b px-4 py-3.5" style={{ borderColor: "var(--line)" }}>
        <div className="min-w-0 flex-1">
          <p className="font-display text-[20px] font-medium uppercase leading-none tracking-[0.03em]">Ask this story</p>
          <p className="mt-1 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
            Answers only from this story&apos;s {sourceCount} source{sourceCount === 1 ? "" : "s"}, with citations, or say they cannot.
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="grid h-11 w-11 flex-none place-items-center border"
            style={{ borderColor: "var(--line)", color: "var(--ink)" }}
          >
            <Close />
          </button>
        )}
      </div>

      {/* No hollow frame before the first question: the line under the title
          already says what this is, and the exchange grows as it happens. */}
      <div ref={scrollRef} className={`flex flex-1 flex-col gap-3.5 overflow-y-auto px-4 ${turns.length ? "min-h-[160px] pb-1 pt-3" : "min-h-0"}`} aria-live="polite">
        {turns.map((t, i) =>
          t.role === "u" ? (
            <div key={i} className="rule-live grid grid-cols-[20px_1fr] gap-x-2 pt-3">
              <span className="font-mono text-[11px] leading-[1.9]" style={{ color: "var(--ink-faint)" }}>Q</span>
              <p className="text-[13.5px] leading-[1.55]" style={{ color: "var(--ink)" }}>{t.text}</p>
            </div>
          ) : (
            <div key={i} className="grid grid-cols-[20px_1fr] gap-x-2 pt-1">
              <span className="font-mono text-[11px] leading-[1.9]" style={{ color: "var(--ink-faint)" }}>A</span>
              <div className="min-w-0">
                {(isRefusal(t) || t.limit) && (
                  <span className="mb-1 block font-mono text-[11px]" style={{ color: "var(--ink)" }}>
                    {t.limit ? "Limit" : "Not in sources"}
                  </span>
                )}
                {t.limit ? (
                  <LimitNote limit={t.limit} next={typeof window === "undefined" ? "/" : window.location.pathname} onUpgrade={onUpgrade} />
                ) : (
                <p
                  className="text-[13.5px] leading-[1.65]"
                  style={{ color: t.error ? "var(--danger)" : isRefusal(t) ? "var(--ink)" : "var(--ink-muted)" }}
                >
                  {t.error ?? <AnswerText text={t.text} citations={t.streaming ? [] : t.citations} />}
                  {t.streaming && (
                    <span
                      className="blink-caret ml-0.5 inline-block h-3.5 w-[7px] align-text-bottom"
                      style={{ background: "var(--ink-muted)" }}
                    />
                  )}
                </p>
                )}
                {!t.streaming && t.structure && <AnswerStructure s={t.structure} citations={t.citations} />}
                {!t.streaming && t.citations.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-[5px]">
                    {t.citations.map((c) => (
                      <a
                        key={c.number}
                        href={c.url ?? undefined}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-[11px] underline-offset-4 hover:underline"
                        style={{ color: "var(--ink-muted)" }}
                      >
                        [{c.number}] {c.source_name}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        )}
        {thinking && (
          <p className="pulse-skel text-xs" style={{ color: "var(--ink-faint)" }}>
            Reading the sources…
          </p>
        )}
      </div>

      {turns.length === 0 && onFollowUp && (
        <div className="flex flex-wrap items-center gap-1.5 px-4 pt-2" aria-label="Dig deeper">
          <span className="mr-1 font-mono text-[11px] uppercase tracking-[0.03em]" style={{ color: "var(--ink-faint)" }}>Dig deeper</span>
          {DIG_DEEPER.map((d) => (
            <button key={d.label} type="button" onClick={() => onFollowUp(d.question)} className="chip h-8 px-3 text-[12.5px]">{d.label}</button>
          ))}
        </div>
      )}
      {/* One row of questions above the input: the story's suggestions before
          the first answer, then the last answer's follow-ups (founder: the row
          changes, rather than the answer growing chips). Nothing while an
          answer is still streaming. */}
      {chips.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-4 pb-2.5 pt-2" aria-label={turns.length ? "Follow-up questions" : "Suggested questions"}>
          {chips.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => (turns.length && onFollowUp ? onFollowUp(q) : onSubmit(q))}
              className="min-h-11 border px-3 py-2 text-left text-[12.5px] transition hover:opacity-75"
              style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2 border-t px-4 pb-[calc(env(safe-area-inset-bottom)+14px)] pt-2.5" style={{ borderColor: "var(--line)" }}>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => onInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask anything about this story…"
          aria-label="Ask"
          className="h-11 min-w-0 flex-1 border px-3 text-[16px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1"
          style={{ borderColor: "var(--line-strong)", background: "var(--bg)", color: "var(--ink)" }}
        />
        <button
          type="button"
          onClick={() => onSubmit(input)}
          aria-label="Send"
          className="grid h-11 w-11 flex-none place-items-center border"
          style={{ borderColor: "var(--ink)", color: "var(--ink)" }}
        >
          <ArrowUp size={15} />
        </button>
      </div>
    </section>
  );
}
