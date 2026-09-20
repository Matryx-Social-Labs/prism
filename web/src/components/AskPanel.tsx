"use client";

import { track } from "@/lib/analytics";
import { Speech } from "@/components/icons";
import { AskShell, type Turn } from "@/components/AskShell";

// The grounded per-story agent as a floating panel at every width (founder
// decision, 2026-09-17): a launcher pill bottom-right from 1024px, the
// ticket's pinned thumb-zone button beneath that; the chat is a 400px panel
// bottom-right on a desk and a bottom sheet over a scrim on a phone. Answers
// stream from the story's own sources with numbered citations; a refusal
// renders as a first-class state.

import { useEffect, useRef, useState } from "react";
import { askQuestion, type AskCitation } from "@/lib/api";

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
    track("Ask");

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
          <AskShell
            sourceCount={sourceCount}
            turns={turns}
            thinking={thinking}
            input={input}
            onInput={setInput}
            onSubmit={submit}
            suggestions={suggestedQuestions}
            onClose={() => setOpen(false)}
            inputRef={inputRef}
            scrollRef={scrollRef}
            className="fixed inset-x-0 bottom-0 z-[46] max-h-[86vh] border-t lg:inset-auto lg:bottom-5 lg:right-5 lg:max-h-[min(640px,calc(100vh-40px))] lg:w-[400px] lg:border"
          />
        </>
      )}
    </>
  );
}
