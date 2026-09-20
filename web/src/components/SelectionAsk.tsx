"use client";

import { useEffect, useState } from "react";
import { useAsk } from "@/components/AskContext";
import { Speech } from "@/components/icons";

const MIN_CHARS = 8;
const MAX_CHARS = 240;

// Select a line of the brief or a quote and a small "Ask about this" chip
// appears over the selection; it opens Ask with the line quoted into the
// question, so "is this number confirmed elsewhere?" needs no retyping. Only
// text inside [data-askable] counts — a selection in the chrome is not a
// question. Fixed to the viewport, so it follows the selection on scroll.
export function SelectionAsk() {
  const ask = useAsk();
  const [hit, setHit] = useState<{ text: string; x: number; y: number } | null>(null);

  useEffect(() => {
    if (!ask) return;
    let raf = 0;
    const read = () => {
      const sel = document.getSelection();
      if (!sel || sel.isCollapsed || sel.rangeCount === 0) return setHit(null);
      const text = sel.toString().replace(/\s+/g, " ").trim();
      if (text.length < MIN_CHARS) return setHit(null);
      const node = sel.anchorNode instanceof Element ? sel.anchorNode : sel.anchorNode?.parentElement;
      if (!node?.closest("[data-askable]")) return setHit(null);
      const r = sel.getRangeAt(0).getBoundingClientRect();
      setHit({ text: text.slice(0, MAX_CHARS), x: r.left + r.width / 2, y: r.top });
    };
    const schedule = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(read); };
    document.addEventListener("selectionchange", schedule);
    window.addEventListener("scroll", schedule, true);
    return () => { cancelAnimationFrame(raf); document.removeEventListener("selectionchange", schedule); window.removeEventListener("scroll", schedule, true); };
  }, [ask]);

  if (!ask || !hit) return null;
  const left = Math.min(Math.max(hit.x, 80), window.innerWidth - 80);
  const above = hit.y > 56;
  return (
    <button
      type="button"
      // mousedown would collapse the selection before click fires.
      onMouseDown={(e) => e.preventDefault()}
      onClick={() => { ask({ prefill: `About this line: “${hit.text}” — `, via: "selection" }); setHit(null); document.getSelection()?.removeAllRanges(); }}
      className="fixed z-[44] inline-flex h-9 -translate-x-1/2 items-center gap-1.5 rounded-full px-3.5 text-[13px] font-semibold"
      style={{ left, top: above ? hit.y - 44 : hit.y + 28, background: "var(--ink)", color: "var(--bg)", boxShadow: "var(--shadow-2)" }}
    >
      <Speech /> Ask about this
    </button>
  );
}
