"use client";

import { ArrowUp, Close } from "@/components/icons";
import type { AskCitation } from "@/lib/api";
import type { KeyboardEvent, RefObject } from "react";

// The Ask panel's body, one markup for the ticket's live panel and the
// landing's scripted one: header, the exchange (Q and A lines on rules, a
// refusal as a first-class state, citations in mono), suggestions, input.

export interface Turn {
  role: "u" | "a";
  text: string;
  citations: AskCitation[];
  error?: string;
  streaming: boolean;
}

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
  suggestions: string[];
  /** Absent on the landing's embedded panel, which has nothing to close. */
  onClose?: () => void;
  inputRef?: RefObject<HTMLInputElement | null>;
  scrollRef?: RefObject<HTMLDivElement | null>;
  className?: string;
  style?: React.CSSProperties;
}) {
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
            className="grid h-8 w-8 flex-none place-items-center border"
            style={{ borderColor: "var(--line)", color: "var(--ink)" }}
          >
            <Close />
          </button>
        )}
      </div>

      <div ref={scrollRef} className="flex min-h-[160px] flex-1 flex-col gap-3.5 overflow-y-auto px-4 pb-1 pt-3" aria-live="polite">
        {turns.length === 0 && (
          <p className="text-[13px] leading-[1.55]" style={{ color: "var(--ink-faint)" }}>
            Ask anything about this story. Every answer cites this story&apos;s own sources, or says it can&apos;t.
          </p>
        )}
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
                {isRefusal(t) && (
                  <span className="mb-1 block font-mono text-[11px]" style={{ color: "var(--ink)" }}>
                    Not in sources
                  </span>
                )}
                <p
                  className="text-[13.5px] leading-[1.65]"
                  style={{ color: t.error ? "var(--danger)" : isRefusal(t) ? "var(--ink)" : "var(--ink-muted)" }}
                >
                  {t.error ?? t.text}
                  {t.streaming && (
                    <span
                      className="blink-caret ml-0.5 inline-block h-3.5 w-[7px] align-text-bottom"
                      style={{ background: "var(--ink-muted)" }}
                    />
                  )}
                </p>
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

      <div className="flex flex-wrap gap-1.5 px-4 pb-2.5 pt-2">
        {suggestions.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onSubmit(q)}
            className="h-8 border px-2.5 text-[12.5px] transition hover:opacity-75"
            style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
          >
            {q}
          </button>
        ))}
      </div>

      <div className="flex gap-2 border-t px-4 pb-[calc(env(safe-area-inset-bottom)+14px)] pt-2.5" style={{ borderColor: "var(--line)" }}>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => onInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask anything about this story…"
          aria-label="Ask"
          className="h-[42px] min-w-0 flex-1 border px-3 text-[16px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1"
          style={{ borderColor: "var(--line-strong)", background: "var(--bg)", color: "var(--ink)" }}
        />
        <button
          type="button"
          onClick={() => onSubmit(input)}
          aria-label="Send"
          className="grid h-[42px] w-[42px] flex-none place-items-center border"
          style={{ borderColor: "var(--ink)", color: "var(--ink)" }}
        >
          <ArrowUp size={15} />
        </button>
      </div>
    </section>
  );
}
