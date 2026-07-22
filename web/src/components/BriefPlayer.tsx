"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { LensMeta } from "@/lib/lenses";

// Read-along player for a lens brief. Uses the browser's built-in Web Speech
// API (speechSynthesis) — no server TTS, no dependency, no model call. The
// brief is spoken one sentence at a time so the active sentence can be
// highlighted (real read-along), which also sidesteps Chrome's ~15s cutoff on
// long single utterances.

// Native sentence segmentation; regex fallback for engines without Intl.Segmenter.
function sentences(text: string): string[] {
  try {
    const seg = new Intl.Segmenter("en", { granularity: "sentence" });
    return [...seg.segment(text)].map((s) => s.segment.trim()).filter(Boolean);
  } catch {
    return (text.match(/[^.!?]+[.!?]*/g) ?? [text]).map((s) => s.trim()).filter(Boolean);
  }
}

function pickVoice(synth: SpeechSynthesis): SpeechSynthesisVoice | null {
  const voices = synth.getVoices();
  if (!voices.length) return null; // not loaded yet → browser default
  const pool = voices.filter((v) => v.lang?.toLowerCase().startsWith("en"));
  const from = pool.length ? pool : voices;
  return (
    from.find((v) => /natural|samantha|siri|google/i.test(v.name)) ??
    from.find((v) => v.localService) ??
    from[0]
  );
}

type Status = "idle" | "playing" | "paused";

export function BriefPlayer({
  brief,
  points,
  meta,
  pointsHeading,
}: {
  brief: string;
  points: string[];
  meta: LensMeta;
  pointsHeading: string;
}) {
  const synthRef = useRef<SpeechSynthesis | null>(null);
  const [supported, setSupported] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [active, setActive] = useState(-1); // index into [...briefSentences, ...points]

  const briefSentences = useMemo(() => sentences(brief), [brief]);

  useEffect(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      synthRef.current = window.speechSynthesis;
      setSupported(true);
    }
    // Cancel on unmount — StoryView remounts this (key={lens}) on lens switch,
    // so switching lenses stops any in-flight narration for free.
    return () => synthRef.current?.cancel();
  }, []);

  function play() {
    const synth = synthRef.current;
    if (!synth) return;
    synth.cancel();
    const blocks = [...briefSentences, ...points];
    const voice = pickVoice(synth);
    blocks.forEach((text, i) => {
      const u = new SpeechSynthesisUtterance(text);
      if (voice) u.voice = voice;
      u.rate = 1;
      u.onstart = () => setActive(i);
      if (i === blocks.length - 1) {
        u.onend = () => {
          setStatus("idle");
          setActive(-1);
        };
      }
      synth.speak(u);
    });
    setStatus("playing");
  }

  function toggle() {
    const synth = synthRef.current;
    if (!synth) return;
    if (status === "idle") play();
    else if (status === "playing") {
      synth.pause(); // ponytail: pause/resume is flaky on iOS Safari; stop still works
      setStatus("paused");
    } else {
      synth.resume();
      setStatus("playing");
    }
  }

  function stop() {
    synthRef.current?.cancel();
    setStatus("idle");
    setActive(-1);
  }

  const spoken = {
    color: "var(--ink)",
    background: meta.bg,
    borderRadius: "3px",
    padding: "1px 2px",
    boxDecorationBreak: "clone" as const,
    WebkitBoxDecorationBreak: "clone" as const,
  };

  return (
    <div className="flex flex-col gap-3.5">
      {supported && (
        <div className="flex items-center gap-2">
          <button
            onClick={toggle}
            aria-label={status === "playing" ? "Pause narration" : status === "paused" ? "Resume narration" : "Listen to this brief"}
            className="flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12px] font-semibold"
            style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}
          >
            {status === "playing" ? (
              <svg aria-hidden width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="5" width="4" height="14" rx="1" />
                <rect x="14" y="5" width="4" height="14" rx="1" />
              </svg>
            ) : (
              <svg aria-hidden width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
                <path d="M7 5l12 7-12 7z" />
              </svg>
            )}
            {status === "playing" ? "Pause" : status === "paused" ? "Resume" : "Listen"}
          </button>
          {status !== "idle" && (
            <button
              onClick={stop}
              aria-label="Stop narration"
              className="flex h-[26px] w-[26px] items-center justify-center rounded-full border"
              style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
            >
              <svg aria-hidden width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="6" width="12" height="12" rx="1.5" />
              </svg>
            </button>
          )}
        </div>
      )}

      <p className="text-[14.5px] leading-[1.7]">
        <span className="font-semibold" style={{ color: meta.color }}>
          Through the {meta.short} lens —{" "}
        </span>
        {briefSentences.map((s, i) => (
          <span key={i} style={active === i ? spoken : { color: "var(--ink-muted)" }}>
            {s}
            {i < briefSentences.length - 1 ? " " : ""}
          </span>
        ))}
      </p>

      {points.length > 0 && (
        <div>
          <h3 className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
            {pointsHeading}
          </h3>
          <ul className="flex flex-col gap-1.5">
            {points.map((pt, i) => {
              const isActive = active === briefSentences.length + i;
              return (
                <li key={pt} className="flex gap-2 text-[13.5px] leading-[1.55]" style={{ color: isActive ? "var(--ink)" : "var(--ink-muted)" }}>
                  <span aria-hidden style={{ color: meta.color }}>
                    ◆
                  </span>
                  <span style={isActive ? spoken : undefined}>{pt}</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
