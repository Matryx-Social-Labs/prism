"use client";

import { useRef, useState } from "react";
import { askQuestion, type AskCitation } from "@/lib/api";

interface Turn {
  question: string;
  answer: string;
  citations: AskCitation[];
  error?: string;
  streaming: boolean;
}

export function AskPanel({
  eventId,
  suggestedQuestions,
}: {
  eventId: string;
  suggestedQuestions: string[];
}) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const sessionRef = useRef<string | null>(null);

  async function submit(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    setBusy(true);
    setInput("");
    setTurns((prev) => [...prev, { question: q, answer: "", citations: [], streaming: true }]);

    const update = (fn: (t: Turn) => Turn) =>
      setTurns((prev) => prev.map((t, i) => (i === prev.length - 1 ? fn(t) : t)));

    try {
      await askQuestion(eventId, q, sessionRef.current, {
        onSession: (sid) => {
          sessionRef.current = sid;
        },
        onToken: (text) => update((t) => ({ ...t, answer: t.answer + text })),
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

  return (
    <div className="rounded-2xl border" style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}>
      <div className="space-y-5 p-5">
        {turns.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.map((q) => (
              <button
                key={q}
                onClick={() => submit(q)}
                disabled={busy}
                className="rounded-full border px-3.5 py-1.5 text-sm transition hover:opacity-70 disabled:opacity-40"
                style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {turns.map((turn, i) => (
          <div key={i} className="space-y-2">
            <p className="font-semibold">You: {turn.question}</p>
            {turn.error ? (
              <p className="text-sm" style={{ color: "var(--danger)" }}>{turn.error}</p>
            ) : (
              <div className="text-sm leading-relaxed" style={{ color: "var(--ink-muted)" }}>
                {turn.answer || (turn.streaming ? "…" : "")}
                {turn.streaming && turn.answer && <span className="animate-pulse">▍</span>}
              </div>
            )}
            {turn.citations.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {turn.citations.map((c) =>
                  c.url ? (
                    <a
                      key={c.number}
                      href={c.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="rounded-full px-2.5 py-0.5 text-xs font-medium transition hover:opacity-75"
                      style={{ background: "var(--lens-cyber-bg)", color: "var(--lens-cyber)" }}
                    >
                      [{c.number}] {c.source_name}
                    </a>
                  ) : (
                    <span key={c.number} className="rounded-full px-2.5 py-0.5 text-xs" style={{ background: "var(--bg-sunken)" }}>
                      [{c.number}] {c.source_name}
                    </span>
                  ),
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void submit(input);
        }}
        className="flex gap-2 border-t p-3.5"
        style={{ borderColor: "var(--line)" }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about this story…"
          className="flex-1 rounded-full border bg-transparent px-4 py-2.5 text-sm outline-none transition focus:opacity-100"
          style={{ borderColor: "var(--line-strong)" }}
          maxLength={2000}
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-full px-5 py-2.5 text-sm font-semibold transition hover:opacity-85 disabled:opacity-40"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          {busy ? "…" : "Ask"}
        </button>
      </form>
    </div>
  );
}
