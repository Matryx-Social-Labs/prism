"use client";

import { useState } from "react";
import { useAsk } from "@/components/AskContext";
import { ArrowUp } from "@/components/icons";

// The Ask affordance that is always in reach. Placed as the last block of the
// record it rides the bottom of the viewport (sticky) while the reader is
// above it and docks under "Ask this story" when they arrive — one input, so
// nothing is duplicated. The suggested questions show while the input is
// focused and empty (Perplexity's habit); the bar itself is just the field.
export function AskBar({ suggestions, sourceCount }: { suggestions: string[]; sourceCount: number }) {
  const ask = useAsk();
  const [q, setQ] = useState("");
  const [focused, setFocused] = useState(false);
  if (!ask) return null;
  const send = (text: string, via: "bar" | "chip") => {
    const t = text.trim();
    if (!t) return;
    ask({ prefill: t, submit: true, via });
    setQ("");
  };
  return (
    <div className="rounded-[24px] border p-1.5" style={{ borderColor: "var(--line-strong)", background: "var(--bg-elevated)", boxShadow: "var(--shadow-2)" }}>
      {focused && !q && suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-2 pb-2 pt-1.5">
          {suggestions.slice(0, 3).map((s) => (
            <button key={s} type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => send(s, "chip")} className="chip chip-q text-[13px]">
              {s}
            </button>
          ))}
        </div>
      )}
      <div className="flex items-center gap-1.5">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.nativeEvent.isComposing) send(q, "bar"); }}
          placeholder={`Ask this story… answers cite its ${sourceCount} ${sourceCount === 1 ? "report" : "reports"}`}
          aria-label="Ask this story"
          className="h-10 min-w-0 flex-1 rounded-full bg-transparent px-3.5 text-[16px] outline-none placeholder:text-[var(--ink-3)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 lg:text-[15px]"
          style={{ color: "var(--ink)" }}
        />
        <button type="button" onClick={() => send(q, "bar")} aria-label="Send" className="grid h-10 w-10 flex-none place-items-center rounded-full" style={{ background: "var(--ink)", color: "var(--bg)" }}>
          <ArrowUp size={15} />
        </button>
      </div>
    </div>
  );
}
