"use client";

import { useState } from "react";
import { useAsk } from "@/components/AskContext";

// The Ask section's bar at the foot of the record (Design System v2 · AskBar):
// the field, one action, the story's own suggested questions, and the promise
// the answers keep. Sending opens the Ask sheet with the question already on
// its way; on the phone the thumb bar is the other way in.
export function AskBar({ suggestions, sourceCount }: { suggestions: string[]; sourceCount: number }) {
  const ask = useAsk();
  const [q, setQ] = useState("");
  if (!ask) return null;
  const send = (text: string, via: "bar" | "chip") => {
    const t = text.trim();
    if (!t) return;
    ask({ prefill: t, submit: true, via });
    setQ("");
  };
  return (
    <div className="grid gap-2.5">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          send(q, "bar");
        }}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            // An IME's Enter confirms a candidate; it is not a question yet.
            if (e.key === "Enter" && e.nativeEvent.isComposing) e.preventDefault();
          }}
          placeholder="Ask this story"
          aria-label="Ask this story"
          className="p-input min-w-0 flex-1"
        />
        <button type="submit" className="p-btn p-btn--primary">Ask</button>
      </form>
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5" aria-label="Suggested questions">
          {suggestions.slice(0, 3).map((s) => (
            <button key={s} type="button" onClick={() => send(s, "chip")} className="p-chip p-chip--q min-h-[44px] lg:min-h-[36px]">
              {s}
            </button>
          ))}
        </div>
      )}
      <p className="text-[13px] leading-[1.4]" style={{ color: "var(--ink-3)" }}>
        Answers cite the {sourceCount} {sourceCount === 1 ? "report" : "reports"} above, or say they can&apos;t.
      </p>
    </div>
  );
}
