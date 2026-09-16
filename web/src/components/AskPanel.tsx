"use client";

import { ArrowUp, Close, Speech } from "@/components/icons";

// The grounded per-story agent as a floating panel at every width (founder
// decision, 2026-09-17): a launcher pill bottom-right from 1024px, the
// ticket's pinned thumb-zone button beneath that; the chat is a 400px panel
// bottom-right on a desk and a bottom sheet over a scrim on a phone. Answers
// stream from the story's own sources with numbered citations; a refusal
// renders as a first-class state.

import { useEffect, useRef, useState } from "react";
import { askQuestion, type AskCitation } from "@/lib/api";

interface Turn {
  role: "u" | "a";
  text: string;
  citations: AskCitation[];
  error?: string;
  streaming: boolean;
}

function isRefusal(turn: Turn): boolean {
  return !turn.streaming && turn.citations.length === 0 && /don'?t cover|refus/i.test(turn.text);
}

export function AskPanel({
  eventId,
  sourceCount,
  suggestedQuestions,
  open: openProp,
  onOpenChange,
  launcher = true,
}: {
  eventId: string;
  sourceCount: number;
  suggestedQuestions: string[];
  // Controlled open: the ticket's pinned thumb-zone button also opens it.
  open?: boolean;
  onOpenChange?: (v: boolean) => void;
  // The bottom-right launcher pill; off when the page supplies its own.
  launcher?: boolean;
}) {
  const [openState, setOpenState] = useState(false);
  const open = openProp !== undefined ? openProp : openState;
  const setOpen = (v: boolean) => (onOpenChange ? onOpenChange(v) : setOpenState(v));
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const sessionRef = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  // `busy` state is read from a render closure, so two taps in the same React
  // batch both see false. A ref latches synchronously.
  const busyRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [turns]);

  // Escape closes; opening lands the caret in the input without scrolling.
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus({ preventScroll: true });
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Stop the stream when the panel unmounts — otherwise it keeps consuming the
  // response and setting state on a dead component.
  useEffect(() => () => abortRef.current?.abort(), []);

  async function submit(question: string) {
    const q = question.trim();
    if (!q || busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setInput("");
    setOpen(true);

    // Capture THIS answer's index at submit time. Targeting `prev.length - 1`
    // meant a second question's turn could receive the first's tokens, and its
    // citations would then be overwritten — attributing one answer's text to
    // another's sources, in a product whose whole claim is grounded citations.
    let answerIndex = -1;
    setTurns((prev) => {
      answerIndex = prev.length + 1;
      return [
        ...prev,
        { role: "u", text: q, citations: [], streaming: false },
        { role: "a", text: "", citations: [], streaming: true },
      ];
    });

    const update = (fn: (t: Turn) => Turn) =>
      setTurns((prev) => prev.map((t, i) => (i === answerIndex ? fn(t) : t)));

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await askQuestion(
        eventId,
        q,
        sessionRef.current,
        {
          onSession: (sid) => {
            sessionRef.current = sid;
          },
          onToken: (text) => update((t) => ({ ...t, text: t.text + text })),
          onCitations: (citations) => update((t) => ({ ...t, citations })),
          onDone: () => update((t) => ({ ...t, streaming: false })),
          onError: (message) => update((t) => ({ ...t, error: message, streaming: false })),
        },
        controller.signal,
      );
    } catch {
      if (!controller.signal.aborted) {
        update((t) => ({ ...t, error: "Connection failed.", streaming: false }));
      }
    } finally {
      busyRef.current = false;
      setBusy(false);
      update((t) => ({ ...t, streaming: false }));
    }
  }

  const thinking = busy && turns.length > 0 && turns[turns.length - 1].text === "";

  return (
    <>
      {launcher && !open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-[45] hidden h-12 items-center gap-2 rounded-full pl-4 pr-5 text-[14.5px] font-semibold transition hover:opacity-90 lg:inline-flex"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          <Speech />
          Ask this story
          <span className="font-mono text-[12px] font-normal opacity-80">{sourceCount} source{sourceCount === 1 ? "" : "s"}</span>
        </button>
      )}
      {open && (
        <>
          <div className="fixed inset-0 z-[45] lg:hidden" style={{ background: "rgba(20,22,19,.35)" }} onClick={() => setOpen(false)} aria-hidden />
          <section
            role="dialog"
            aria-label="Ask this story"
            className="fixed inset-x-0 bottom-0 z-[46] flex max-h-[86vh] flex-col overflow-hidden border-t lg:inset-auto lg:bottom-5 lg:right-5 lg:max-h-[min(640px,calc(100vh-40px))] lg:w-[400px] lg:border"
            style={{ borderColor: "var(--line-strong)", background: "var(--bg-elevated)" }}
          >
            <div className="flex items-baseline gap-3 border-b px-4 py-3.5" style={{ borderColor: "var(--line)" }}>
              <div className="min-w-0 flex-1">
                <p className="font-display text-[20px] font-medium uppercase leading-none tracking-[0.03em]">Ask this story</p>
                <p className="mt-1 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
                  Answers only from this story&apos;s {sourceCount} source{sourceCount === 1 ? "" : "s"}, with citations, or say they cannot.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close"
                className="grid h-8 w-8 flex-none place-items-center border"
                style={{ borderColor: "var(--line)", color: "var(--ink)" }}
              >
                <Close />
              </button>
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
              {suggestedQuestions.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => submit(q)}
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
                onChange={(e) => setInput(e.target.value)}
                // isComposing: for Devanagari/Tamil/Telugu IMEs, Enter confirms the
                // candidate. Submitting on it sends a half-composed question.
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.nativeEvent.isComposing) submit(input);
                }}
                placeholder="Ask anything about this story…"
                aria-label="Ask"
                className="h-[42px] min-w-0 flex-1 border px-3 text-[16px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1"
                style={{ borderColor: "var(--line-strong)", background: "var(--bg)", color: "var(--ink)" }}
              />
              <button
                type="button"
                onClick={() => submit(input)}
                aria-label="Send"
                className="grid h-[42px] w-[42px] flex-none place-items-center border"
                style={{ borderColor: "var(--ink)", color: "var(--ink)" }}
              >
                <ArrowUp size={15} />
              </button>
            </div>
          </section>
        </>
      )}
    </>
  );
}
