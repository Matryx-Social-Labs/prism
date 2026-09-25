"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { LensMeta } from "@/lib/lenses";
import type { EntityOut, SpeakerClaims } from "@/lib/api";
import { EntityText } from "@/components/EntityText";
import { Pause, Play } from "@/components/icons";
import { markBlocks } from "@/lib/entities";

// Read-along for a lens brief (Design System v2 · LensBrief + BriefPlayer).
// Uses the browser's built-in Web Speech API (speechSynthesis) — no server
// TTS, no dependency, no model call. The brief is spoken one sentence at a
// time so the active sentence can be highlighted in place (real read-along),
// which also sidesteps Chrome's ~15s cutoff on long single utterances. The
// text sits in the lens block; the player sits beneath it.

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

export interface Narration {
  supported: boolean;
  status: Status;
  /** Index into the blocks being spoken; -1 when silent. */
  active: number;
  total: number;
  toggle: () => void;
  stop: () => void;
}

/** Speaks `blocks` one at a time. A new `resetKey` (another lens) stops it. */
export function useNarration(blocks: string[], resetKey: string): Narration {
  const synthRef = useRef<SpeechSynthesis | null>(null);
  const [supported, setSupported] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [active, setActive] = useState(-1);

  useEffect(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      synthRef.current = window.speechSynthesis;
      setSupported(true);
    }
    return () => synthRef.current?.cancel();
  }, []);

  useEffect(() => {
    synthRef.current?.cancel();
    setStatus("idle");
    setActive(-1);
  }, [resetKey]);

  function play() {
    const synth = synthRef.current;
    if (!synth) return;
    synth.cancel();
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

  return { supported, status, active, total: blocks.length, toggle, stop };
}

/**
 * The brief's text inside the lens block. Three or more sentences print as
 * points, one fact per line (founder, 2026-09-18; NN/G "How Users Read on the
 * Web": readers scan); one or two stay a sentence. Every line is marked for
 * entities and lit while it is read aloud.
 */
export function BriefText({
  sentences: briefSentences,
  points,
  active,
  meta,
  pointsHeading,
  entities = [],
  claims = [],
}: {
  sentences: string[];
  points: string[];
  active: number;
  meta: LensMeta;
  pointsHeading: string;
  entities?: EntityOut[];
  claims?: SpeakerClaims[];
}) {
  // One entity mark per passage — sentences first, then the points — computed
  // once, purely, so the server and the client mark the same words.
  const marked = useMemo(() => markBlocks([...briefSentences, ...points], entities), [briefSentences, points, entities]);
  const pro = meta.slug !== "reader";
  const spoken = { color: "var(--ink)", background: "var(--accent-soft)", borderRadius: "2px", boxDecorationBreak: "clone" as const, WebkitBoxDecorationBreak: "clone" as const };
  const square = (top: number) => <span aria-hidden className="h-1.5 w-1.5 shrink-0" style={{ marginTop: top, background: pro ? "var(--lens)" : "var(--ink)" }} />;

  return (
    <div className="grid gap-3">
      {briefSentences.length >= 3 ? (
        <ul className="grid gap-2" style={{ font: "var(--t-body-l)", color: "var(--ink)" }}>
          {briefSentences.map((s, i) => (
            <li key={i} className="flex gap-3">
              {square(12)}
              <span className="min-w-0" style={active === i ? spoken : undefined}>
                <EntityText text={s} entities={entities} claims={claims} segments={marked[i]} />
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ font: "var(--t-body-l)", color: "var(--ink)" }}>
          {briefSentences.map((s, i) => (
            <span key={i} style={active === i ? spoken : undefined}>
              <EntityText text={s} entities={entities} claims={claims} segments={marked[i]} />
              {i < briefSentences.length - 1 ? " " : ""}
            </span>
          ))}
        </p>
      )}

      {points.length > 0 && (
        <div>
          <h3 className="p-eyebrow mb-1.5" style={pro ? { color: "var(--lens)" } : undefined}>{pointsHeading}</h3>
          <ul className="grid gap-1.5">
            {points.map((pt, i) => {
              const k = briefSentences.length + i;
              return (
                <li key={pt} className="flex gap-2.5" style={{ font: "var(--t-body-s)", color: active === k ? "var(--ink)" : "var(--ink-2)" }}>
                  {square(9)}
                  <span className="min-w-0" style={active === k ? spoken : undefined}><EntityText text={pt} entities={entities} claims={claims} segments={marked[k]} /></span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

/** The player beneath the lens block: Listen · Pause · Resume · Stop, and where it is, counted. */
export function ListenBox({ narration: n }: { narration: Narration }) {
  if (!n.supported || n.total === 0) return null;
  return (
    <div className="mt-2.5 flex flex-wrap items-center gap-2 rounded-[var(--r-md)] border p-3" style={{ borderColor: "var(--line)", background: "var(--surface)" }}>
      <button
        type="button"
        onClick={n.toggle}
        aria-label={n.status === "playing" ? "Pause narration" : n.status === "paused" ? "Resume narration" : "Listen to this brief"}
        className="p-btn p-btn--secondary p-btn--sm"
      >
        {n.status === "playing" ? <Pause size={14} /> : <Play size={14} />}
        {n.status === "playing" ? "Pause" : n.status === "paused" ? "Resume" : "Listen"}
      </button>
      {n.status !== "idle" && (
        <button type="button" onClick={n.stop} aria-label="Stop narration" className="p-btn p-btn--ghost p-btn--sm">Stop</button>
      )}
      <span className="p-count ml-auto">
        {n.status === "idle" ? `${n.total} ${n.total === 1 ? "sentence" : "sentences"} · read aloud` : `${Math.max(0, n.active) + 1} / ${n.total}`}
      </span>
    </div>
  );
}
