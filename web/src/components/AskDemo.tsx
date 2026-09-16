"use client";

import { useEffect, useRef, useState } from "react";
import { AskShell, type Turn } from "@/components/AskShell";

// The landing's Ask illustration (founder decision 4, 2026-09-17): the very
// panel the ticket uses, playing a scripted exchange on the story the page
// is talking about when it scrolls into view. A question is typed into the
// input and sent, the answer streams in with its citations, the second
// question meets a refusal. Under reduced motion the finished exchange is
// simply there. Nothing here calls the agent; the page says ILLUSTRATION.

const SCRIPT: { q: string; a: string; cites: Turn["citations"] }[] = [
  {
    q: "Why was the order rushed before winter?",
    a: "The transport minister cited the November smog forecast [2]; two outlets add a pending court deadline [4][5].",
    cites: [
      { number: 2, article_id: "d2", source_name: "The Hindu", url: null },
      { number: 4, article_id: "d4", source_name: "Hindustan Times", url: null },
      { number: 5, article_id: "d5", source_name: "Dainik Bhaskar", url: null },
    ],
  },
  { q: "Will Mumbai follow?", a: "The 31 reports on this story do not say. Ask about what they cover, or open the sources.", cites: [] },
];
const SOURCES = 31;
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function AskDemo() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  const played = useRef(false);

  useEffect(() => {
    const el = wrap.current; if (!el) return;
    const finished = () => SCRIPT.flatMap((s) => [{ role: "u" as const, text: s.q, citations: [], streaming: false }, { role: "a" as const, text: s.a, citations: s.cites, streaming: false }]);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setTurns(finished()); return; }
    let alive = true;
    const play = async () => {
      for (const s of SCRIPT) {
        for (let k = 1; k <= s.q.length; k++) { if (!alive) return; setInput(s.q.slice(0, k)); await wait(28); }
        await wait(350); if (!alive) return;
        setInput("");
        setTurns((t) => [...t, { role: "u", text: s.q, citations: [], streaming: false }, { role: "a", text: "", citations: [], streaming: true }]);
        setThinking(true); await wait(700); setThinking(false);
        const words = s.a.split(" ");
        for (let i = 1; i <= words.length; i++) {
          if (!alive) return;
          const text = words.slice(0, i).join(" ");
          setTurns((t) => t.map((x, k) => (k === t.length - 1 ? { ...x, text } : x)));
          await wait(55);
        }
        setTurns((t) => t.map((x, k) => (k === t.length - 1 ? { ...x, citations: s.cites, streaming: false } : x)));
        await wait(1100);
      }
    };
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting) && !played.current) { played.current = true; play(); } }, { threshold: 0.5 });
    io.observe(el);
    return () => { alive = false; io.disconnect(); };
  }, []);

  return (
    <div ref={wrap} className="max-w-[400px]">
      <AskShell
        sourceCount={SOURCES}
        turns={turns}
        thinking={thinking}
        input={input}
        onInput={setInput}
        onSubmit={() => {}}
        suggestions={["What led to this?", "Who is affected?", "Will Mumbai follow?"]}
        className="border"
      />
    </div>
  );
}
