"use client";

// The grounded per-story agent, redesigned as a floating chat panel
// (collapsed pill bottom-right → chat). Answers stream from the story's own
// sources with numbered citations; a refusal renders as a first-class state.

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
  docked = false,
}: {
  eventId: string;
  sourceCount: number;
  suggestedQuestions: string[];
  // docked: render inline (in the story rail) instead of a floating pill — no
  // fixed positioning, always open, and the rail card supplies the header.
  docked?: boolean;
}) {
  const [open, setOpen] = useState(docked);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const sessionRef = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [turns]);

  async function submit(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    setBusy(true);
    setInput("");
    setOpen(true);
    setTurns((prev) => [
      ...prev,
      { role: "u", text: q, citations: [], streaming: false },
      { role: "a", text: "", citations: [], streaming: true },
    ]);

    const update = (fn: (t: Turn) => Turn) =>
      setTurns((prev) => prev.map((t, i) => (i === prev.length - 1 ? fn(t) : t)));

    try {
      await askQuestion(eventId, q, sessionRef.current, {
        onSession: (sid) => {
          sessionRef.current = sid;
        },
        onToken: (text) => update((t) => ({ ...t, text: t.text + text })),
        onCitations: (citations) => update((t) => ({ ...t, citations })),
        onDone: () => update((t) => ({ ...t, streaming: false })),
        onError: (message) => update((t) => ({ ...t, error: message, streaming: false })),
      });
    } catch {
      update((t) => ({ ...t, error: "Connection failed.", streaming: false }));
    } finally {
      setBusy(false);
      update((t) => ({ ...t, streaming: false }));
    }
  }

  const thinking = busy && turns.length > 0 && turns[turns.length - 1].text === "";

  return (
    <div className={docked ? "w-full" : "fixed bottom-[18px] right-[18px] z-[70] w-[396px] max-w-[calc(100vw-24px)]"}>
      {!open ? (
        <button
          onClick={() => setOpen(true)}
          className="float-right flex items-center gap-2 rounded-full border px-5 py-3 text-[13.5px] font-semibold transition hover:opacity-90"
          style={{
            borderColor: "var(--line-strong)",
            background: "var(--ink)",
            color: "var(--bg)",
            boxShadow: "var(--shadow-pop)",
          }}
        >
          <span className="spectrum-text text-[15px]" aria-hidden>
            ◮
          </span>
          Ask this story
        </button>
      ) : (
        <div
          className={`flex flex-col overflow-hidden ${docked ? "" : "rounded-[20px] border"}`}
          style={
            docked
              ? undefined
              : { borderColor: "var(--line)", background: "var(--bg-elevated)", boxShadow: "var(--shadow-pop)" }
          }
        >
          {!docked && (
            <div className="flex items-center gap-2.5 border-b px-[18px] py-3.5" style={{ borderColor: "var(--line)" }}>
              <span className="spectrum-text text-base" aria-hidden>
                ◮
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">Ask this story</p>
                <p className="text-[11px]" style={{ color: "var(--ink-faint)" }}>
                  Answers only from this story&apos;s {sourceCount} source{sourceCount === 1 ? "" : "s"} — with
                  citations.
                </p>
              </div>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close"
                className="px-1.5 py-0.5 text-base"
                style={{ color: "var(--ink-faint)" }}
              >
                ✕
              </button>
            </div>
          )}

          <div
            ref={scrollRef}
            className={`flex flex-col gap-3.5 overflow-y-auto ${docked ? "max-h-64 px-4 pt-3" : "max-h-80 px-[18px] py-4"}`}
          >
            {docked && turns.length === 0 && (
              <p className="text-[12px] leading-[1.55]" style={{ color: "var(--ink-faint)" }}>
                Ask anything about this story — every answer cites this story&apos;s own sources, or
                says it can&apos;t.
              </p>
            )}
            {turns.map((t, i) =>
              t.role === "u" ? (
                <div key={i} className="max-w-[85%] self-end">
                  <p
                    className="rounded-[14px] px-3.5 py-2 text-[13px] leading-[1.55]"
                    style={{ background: "var(--bg-sunken)", color: "var(--ink)" }}
                  >
                    {t.text}
                  </p>
                </div>
              ) : (
                <div key={i} className="max-w-[95%] self-start">
                  {isRefusal(t) && (
                    <span
                      className="mb-1.5 inline-block rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                      style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
                    >
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
                          className="rounded-full border px-[9px] py-0.5 font-mono text-[10px] font-medium no-underline"
                          style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
                        >
                          [{c.number}] {c.source_name}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              )
            )}
            {thinking && (
              <p className="pulse-skel text-xs" style={{ color: "var(--ink-faint)" }}>
                Reading the sources…
              </p>
            )}
          </div>

          <div className={`flex flex-wrap gap-1.5 pb-3 ${docked ? "px-4 pt-3" : "px-[18px]"}`}>
            {suggestedQuestions.map((q) => (
              <button
                key={q}
                onClick={() => submit(q)}
                className="rounded-full border px-3 py-[5px] text-xs font-medium transition hover:opacity-75"
                style={{ borderColor: "var(--line)", background: "var(--bg)", color: "var(--ink-muted)" }}
              >
                {q}
              </button>
            ))}
          </div>

          <div className={`flex gap-2 border-t pt-3 ${docked ? "px-4 pb-4" : "px-[18px] pb-4"}`} style={{ borderColor: "var(--line)" }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit(input)}
              placeholder="Ask anything about this story…"
              className="min-w-0 flex-1 rounded-full border px-4 py-[9px] text-[13px] outline-none"
              style={{ borderColor: "var(--line)", background: "var(--bg)", color: "var(--ink)" }}
            />
            <button
              onClick={() => submit(input)}
              aria-label="Send"
              className="h-[38px] w-[38px] rounded-full text-[15px]"
              style={{ background: "var(--ink)", color: "var(--bg)" }}
            >
              ↑
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
