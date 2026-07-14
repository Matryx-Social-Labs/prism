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
    <div className="rounded-lg border border-stone-200 dark:border-stone-800">
      <div className="space-y-4 p-4">
        {turns.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.map((q) => (
              <button
                key={q}
                onClick={() => submit(q)}
                disabled={busy}
                className="rounded-full border border-stone-300 px-3 py-1 text-sm hover:bg-stone-100 disabled:opacity-50 dark:border-stone-700 dark:hover:bg-stone-900"
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
              <p className="text-sm text-red-600">{turn.error}</p>
            ) : (
              <div className="text-sm leading-relaxed text-stone-700 dark:text-stone-300">
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
                      className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-800 hover:bg-blue-200 dark:bg-blue-950 dark:text-blue-300"
                    >
                      [{c.number}] {c.source_name}
                    </a>
                  ) : (
                    <span key={c.number} className="rounded bg-stone-100 px-1.5 py-0.5 text-xs dark:bg-stone-900">
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
        className="flex gap-2 border-t border-stone-200 p-3 dark:border-stone-800"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about this story…"
          className="flex-1 rounded-md border border-stone-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-stone-500 dark:border-stone-700"
          maxLength={2000}
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40 dark:bg-stone-100 dark:text-stone-900"
        >
          {busy ? "…" : "Ask"}
        </button>
      </form>
    </div>
  );
}
