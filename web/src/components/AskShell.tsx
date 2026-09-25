"use client";

import Link from "next/link";
import { Close } from "@/components/icons";
import type { AskCitation, AskLimit, AskStructure } from "@/lib/api";
import type { FormEvent, KeyboardEvent, RefObject } from "react";

// The Ask panel's body, one markup for the record's live sheet and the
// landing's scripted one (Design System v2 · AskAnswer, AskPanel, AskBar,
// AskLimitNote): the question as a bubble, the answer in the reading voice
// with its [n] chips, the table and "Not in the reports" after the prose, the
// sources it cited, then the questions it can answer next; a refusal and a
// limit are first-class states. The input and the grounding line are the foot.

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

/** The answer's anatomy after the prose: table · what the reports don't say. (Its follow-ups take the question row.) */
export function AnswerStructure({ s, citations }: { s: AskStructure; citations: AskCitation[] }) {
  const [left, right] = s.columns.length === 2 ? s.columns : ["", ""];
  const numeric = s.kind === "timeline" || s.kind === "numbers";
  return (
    <div className="grid gap-3">
      {s.rows.length > 0 && (
        <div className="p-hide-scroll overflow-x-auto">
          <table className="p-table" aria-label={s.kind ?? "table"}>
            {(left || right) && (
              <thead>
                <tr>
                  <th scope="col">{left}</th>
                  <th scope="col">{right}</th>
                </tr>
              </thead>
            )}
            <tbody>
              {s.rows.map((r, i) => (
                <tr key={i}>
                  <td className={`${s.kind === "who_said" ? "font-semibold" : ""} ${numeric ? "whitespace-nowrap font-mono text-[12px]" : ""}`}>{r.a}</td>
                  <td className={s.kind === "who_said" ? "font-record italic" : ""}>
                    {s.kind === "who_said" ? <>“{r.b}”</> : r.b} {r.n && <AnswerText text={r.n} citations={citations} />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {s.gaps && (
        <p className="border-l-2 pl-2.5 text-[13.5px] leading-[1.45]" style={{ borderColor: "var(--line-strong)", color: "var(--ink-3)" }}>
          <span>Not in the reports:</span> <span>{s.gaps}</span>
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
        return c?.url ? (
          <a key={i} href={c.url} target="_blank" rel="noopener noreferrer" title={c.source_name} className="p-cite">{part}</a>
        ) : (
          <span key={i} className="p-cite">{part}</span>
        );
      })}
    </>
  );
}

export type UpgradeAsk = { reason: "ask-limit" | "ask-rest"; used?: number; limit?: number };

/** What a refused question tells the reader, and the one action that helps. */
export function LimitNote({ limit, next, onUpgrade }: { limit: AskLimit; next: string; onUpgrade?: (o: UpgradeAsk) => void }) {
  const action = "font-semibold";
  const plusLink = (label: string, o: UpgradeAsk) =>
    onUpgrade ? (
      <button type="button" onClick={() => onUpgrade(o)} className={action} style={{ color: "var(--accent)" }}>{label}</button>
    ) : (
      <Link href="/plus" className={action} style={{ color: "var(--accent)" }}>{label}</Link>
    );
  let body: React.ReactNode;
  if (limit.retry_after_s) body = <span>One question at a time — try again in a minute.</span>;
  else if (limit.status === 503) {
    body = (
      <>
        <span>Ask is resting for today for free readers. It is back at midnight UTC.</span>
        {limit.plus_helps && plusLink("Plus stays on →", { reason: "ask-rest" })}
      </>
    );
  } else if (limit.signin_helps) {
    body = (
      <>
        <span>That was your last free question here.</span>
        <Link href={`/signin?next=${encodeURIComponent(next)}`} className={action} style={{ color: "var(--accent)" }}>Sign in for 10 a day →</Link>
      </>
    );
  } else {
    body = (
      <>
        <span>You have asked {limit.used ?? limit.limit} of {limit.limit} questions today.</span>
        {limit.plus_helps && plusLink("Plus is 100 a day →", { reason: "ask-limit", used: limit.used, limit: limit.limit })}
      </>
    );
  }
  return (
    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 rounded-[var(--r-md)] px-3 py-2.5 text-[13.5px] leading-[1.45]" style={{ background: "var(--sunken)", color: "var(--ink-2)" }}>
      {body}
    </div>
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

function Answer({ t, onUpgrade, titleOf }: { t: Turn; onUpgrade?: (o: UpgradeAsk) => void; titleOf?: (articleId: string) => string | undefined }) {
  if (t.limit) {
    return (
      <div className="grid gap-1.5">
        <span className="p-badge p-badge--dashed justify-self-start">Limit</span>
        <LimitNote limit={t.limit} next={typeof window === "undefined" ? "/" : window.location.pathname} onUpgrade={onUpgrade} />
      </div>
    );
  }
  if (t.error) return <div className="p-alert p-alert--error" role="alert">{t.error}</div>;
  if (isRefusal(t)) {
    return (
      <div className="grid gap-1.5 rounded-[var(--r-md)] border border-dashed p-3.5" style={{ borderColor: "var(--line-strong)" }}>
        <span className="p-badge p-badge--dashed justify-self-start">Not in sources</span>
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}><AnswerText text={t.text} citations={[]} /></p>
      </div>
    );
  }
  // Nothing written yet: the panel's "Reading the sources…" says so.
  if (t.streaming && !t.text) return null;
  return (
    <div className="grid gap-3">
      <p style={{ font: "var(--t-body)", color: "var(--ink)", overflowWrap: "anywhere" }}>
        <AnswerText text={t.text} citations={t.streaming ? [] : t.citations} />
        {t.streaming && <span className="p-caret" aria-hidden />}
      </p>
      {!t.streaming && t.structure && <AnswerStructure s={t.structure} citations={t.citations} />}
      {!t.streaming && t.citations.length > 0 && (
        <ol className="grid gap-1" aria-label="Sources">
          {t.citations.map((c) => {
            const title = titleOf?.(c.article_id);
            return (
              <li key={c.number} className="grid grid-cols-[28px_minmax(0,1fr)] gap-1.5 text-[13px] leading-[1.4]" style={{ color: "var(--ink-2)" }}>
                <span className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>[{c.number}]</span>
                <span style={{ overflowWrap: "anywhere" }}>
                  {c.url ? (
                    <a href={c.url} target="_blank" rel="noopener noreferrer" className="font-semibold hover:underline" style={{ color: "var(--ink)" }}>{c.source_name}</a>
                  ) : (
                    <b className="font-semibold" style={{ color: "var(--ink)" }}>{c.source_name}</b>
                  )}
                  {title && <> · {title}</>}
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
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
  titleOf,
  chrome = true,
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
  /** A cited report's own headline, printed beside its outlet. */
  titleOf?: (articleId: string) => string | undefined;
  /** False inside a Sheet, which carries the title, the close and the dialog role. */
  chrome?: boolean;
  className?: string;
  style?: React.CSSProperties;
}) {
  const last = turns[turns.length - 1];
  const chips = turns.length === 0 ? suggestions : last?.role === "a" && !last.streaming ? (last.structure?.followups ?? []) : [];
  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    // isComposing: for Devanagari/Tamil/Telugu IMEs, Enter confirms the
    // candidate. Submitting on it sends a half-composed question.
    if (e.key === "Enter" && !e.nativeEvent.isComposing) {
      e.preventDefault();
      onSubmit(input);
    }
  };
  const onForm = (e: FormEvent) => e.preventDefault();

  const body = (
    <>
      <div ref={scrollRef} className="grid min-h-0 flex-1 content-start gap-3.5 overflow-y-auto px-5 pb-4 pt-1" aria-live="polite">
        {turns.length === 0 && onFollowUp && (
          <div aria-label="Dig deeper">
            <p className="p-eyebrow mb-2">Dig deeper</p>
            <div className="flex flex-wrap gap-1.5">
              {DIG_DEEPER.map((d) => (
                <button key={d.label} type="button" onClick={() => onFollowUp(d.question)} className="p-chip min-h-[44px] lg:min-h-[36px]">{d.label}</button>
              ))}
            </div>
          </div>
        )}
        {turns.map((t, i) =>
          t.role === "u" ? (
            <p key={i} className="max-w-[88%] justify-self-end rounded-[var(--r-lg)] px-3.5 py-2.5 text-[15px] font-medium leading-[1.45]" style={{ background: "var(--sunken)", color: "var(--ink)", overflowWrap: "anywhere" }}>
              {t.text}
            </p>
          ) : (
            <Answer key={i} t={t} onUpgrade={onUpgrade} titleOf={titleOf} />
          ),
        )}
        {thinking && <p className="p-count">Reading the sources…</p>}
        {/* One row of questions: the story's suggestions before the first
            answer, then the last answer's follow-ups (founder: the row
            changes, rather than the answer growing chips). Nothing while an
            answer is still streaming. */}
        {chips.length > 0 && (
          <div className="flex flex-wrap gap-1.5" aria-label={turns.length ? "Follow-up questions" : "Suggested questions"}>
            {chips.map((q) => (
              <button key={q} type="button" onClick={() => (turns.length && onFollowUp ? onFollowUp(q) : onSubmit(q))} className="p-chip p-chip--q min-h-[44px] lg:min-h-[36px]">
                {q}
              </button>
            ))}
          </div>
        )}
      </div>

      <form onSubmit={onForm} className="grid gap-2 border-t px-5 pb-[calc(env(safe-area-inset-bottom)+14px)] pt-3" style={{ borderColor: "var(--line)" }}>
        <div className="flex gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => onInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask anything about this story"
            aria-label="Ask"
            className="p-input min-w-0 flex-1"
          />
          <button type="button" onClick={() => onSubmit(input)} aria-label="Ask (send)" className="p-btn p-btn--primary">
            Ask
          </button>
        </div>
        <p className="text-[13px] leading-[1.4]" style={{ color: "var(--ink-3)" }}>
          Answers only from this story&apos;s {sourceCount} {sourceCount === 1 ? "source" : "sources"}, with citations, or say they can&apos;t.
        </p>
      </form>
    </>
  );

  if (!chrome) return <div className="flex min-h-0 flex-1 flex-col">{body}</div>;
  return (
    <section role="dialog" aria-label="Ask this story" className={`flex flex-col overflow-hidden ${className}`} style={{ background: "var(--elevated)", borderColor: "var(--line)", borderRadius: "var(--r-lg)", ...style }}>
      <div className="flex items-center gap-2 pb-1.5 pl-5 pr-3 pt-2.5">
        <span className="min-w-0 flex-1" style={{ font: "var(--t-title-s)" }}>Ask this story</span>
        <span className="p-count">answers cite the reports</span>
        {onClose && (
          <button type="button" onClick={onClose} aria-label="Close" className="p-iconbtn">
            <Close size={16} />
          </button>
        )}
      </div>
      {body}
    </section>
  );
}
