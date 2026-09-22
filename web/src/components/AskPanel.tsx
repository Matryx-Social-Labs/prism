"use client";

import { track } from "@/lib/analytics";
import { Speech } from "@/components/icons";
import { AskShell, type Turn, type UpgradeAsk } from "@/components/AskShell";
import { UpgradeSheet } from "@/components/UpgradeSheet";
import type { AskOpen } from "@/components/AskContext";
import { useSession } from "@/lib/session";

// The grounded per-story agent as one sheet at every width: a bottom sheet
// over a scrim on the phone, a right-side drawer under the top bar on a desk
// so the record stays readable beside the answer (founder, 2026-09-20; it was
// a 400px box bottom-right). Opened by the persistent bar, the thumb-zone
// button, a selection, a quote or an entity (AskContext), which may hand it a
// question to show or to send. Answers stream from the story's own sources
// with numbered citations; a refusal and a limit are first-class states.

import { useEffect, useRef, useState } from "react";
import { askQuestion } from "@/lib/api";

export function AskPanel({
  eventId,
  sourceCount,
  suggestedQuestions,
  open: openProp,
  onOpenChange,
  launcher = true,
  request = null,
}: {
  eventId: string;
  sourceCount: number;
  suggestedQuestions: string[];
  // Controlled open: the ticket's pinned thumb-zone button also opens it.
  open?: boolean;
  onOpenChange?: (v: boolean) => void;
  // The bottom-right launcher pill; off when the page supplies its own.
  launcher?: boolean;
  // What an entry point opened us with; `nonce` makes the same text twice a new request.
  request?: (AskOpen & { nonce: number }) | null;
}) {
  const session = useSession();
  const [openState, setOpenState] = useState(false);
  const [upgrade, setUpgrade] = useState<UpgradeAsk | null>(null);
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

  // An entry point's request: send it, or put it in the input to finish. The
  // caret goes to the end so a quoted line reads as the start of a question.
  const viaRef = useRef<AskOpen["via"]>("foot");
  useEffect(() => {
    if (!request) return;
    viaRef.current = request.via;
    if (request.submit && request.prefill) {
      void submit(request.prefill);
      return;
    }
    if (request.prefill !== undefined) {
      setInput(request.prefill);
      requestAnimationFrame(() => {
        const el = inputRef.current;
        if (!el) return;
        el.focus({ preventScroll: true });
        el.setSelectionRange(el.value.length, el.value.length);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request?.nonce]);

  async function submit(question: string) {
    const q = question.trim();
    if (!q || busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setInput("");
    setOpen(true);
    track("Ask", { via: viaRef.current });
    viaRef.current = "foot";

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
          onStructure: (structure) => update((t) => ({ ...t, structure })),
          onCitations: (citations) => update((t) => ({ ...t, citations })),
          onDone: () => update((t) => ({ ...t, streaming: false })),
          onError: (message, limit) => update((t) => ({ ...t, error: limit ? undefined : message, limit, streaming: false })),
        },
        controller.signal,
        // The account's allowance and model, not the anonymous three: without
        // the token every signed-in reader was capped as a stranger.
        session?.token,
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
            onFollowUp={(q) => { viaRef.current = "chip"; void submit(q); }}
            onUpgrade={setUpgrade}
            suggestions={suggestedQuestions}
            onClose={() => setOpen(false)}
            inputRef={inputRef}
            scrollRef={scrollRef}
            className="ask-sheet fixed inset-x-0 bottom-0 z-[46] max-h-[86vh] border-t lg:inset-auto lg:bottom-0 lg:right-0 lg:top-[var(--topbar)] lg:max-h-none lg:w-[420px] lg:border-l lg:border-t-0"
          />
        </>
      )}
      <UpgradeSheet open={upgrade !== null} onClose={() => setUpgrade(null)} reason={upgrade?.reason} used={upgrade?.used} limit={upgrade?.limit} />
    </>
  );
}
