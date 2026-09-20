"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { ClipOut } from "@/lib/api";
import { relativeTime } from "@/lib/dateline";
import { Headphones, Pause, Play, SkipNext } from "@/components/icons";

/**
 * "Heard on": the stretches of news podcasts that discussed this story, in the
 * hosts' own words (DESIGN.md § Podcast clip).
 *
 * One <audio> for the section. Play on a card seeks the publisher's own file
 * to the clip's start; at the clip's end the queue advances to the next card
 * (another episode if need be) unless the reader chose to keep listening. The
 * transcript is the card's body — the first sentence is the headline — and its
 * words step back as they are spoken (the unsaid stand in ink). Nothing is ours: the audio, the words and the
 * art are the show's, named on the card, with the whole episode one tap away.
 *
 * Hosts stitch ads in per request, so the file the browser loads may not be
 * the file we transcribed. `shift` is the difference in duration between the
 * two; a pre-roll ad is the common case and shifts every offset by the same
 * amount, so the seek and the read-along both add it.
 */
export const PODCAST_CLIPS = process.env.NEXT_PUBLIC_PODCAST_CLIPS !== "0";
const ADVANCE_PAUSE_MS = 400;
const SHIFT_TOLERANCE_S = 1.5;

export function clipShift(loadedDuration: number, transcribedDuration: number | null | undefined): number {
  if (!transcribedDuration || !Number.isFinite(loadedDuration) || loadedDuration <= 0) return 0;
  const d = loadedDuration - transcribedDuration;
  return Math.abs(d) < SHIFT_TOLERANCE_S ? 0 : d;
}

function mmss(s: number): string {
  const t = Math.max(0, Math.round(s));
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
}

export function Clips({ clips }: { clips: ClipOut[] }) {
  const audio = useRef<HTMLAudioElement>(null);
  const [active, setActive] = useState<number>(-1);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0); // in the loaded file's clock
  const [shift, setShift] = useState(0);
  const [freeRun, setFreeRun] = useState(false); // "keep listening": past end_s
  const advancing = useRef<number | null>(null);
  const pendingSeek = useRef<number | null>(null);

  const current = active >= 0 ? clips[active] : null;

  const seekTo = useCallback((el: HTMLAudioElement, clip: ClipOut) => {
    const sh = clipShift(el.duration, clip.audio_duration_s);
    setShift(sh);
    el.currentTime = Math.max(0, clip.start_s + sh);
  }, []);

  const play = useCallback(
    (i: number) => {
      const el = audio.current;
      const clip = clips[i];
      if (!el || !clip) return;
      if (advancing.current) window.clearTimeout(advancing.current);
      setFreeRun(false);
      setActive(i);
      const sameFile = el.currentSrc === clip.audio_url || el.src === clip.audio_url;
      if (sameFile && el.readyState >= 1) {
        seekTo(el, clip);
        void el.play();
      } else {
        pendingSeek.current = i;
        el.src = clip.audio_url;
        el.load();
        // Seek once metadata is in (see onLoadedMetadata), then play.
      }
    },
    [clips, seekTo],
  );

  const pause = useCallback(() => audio.current?.pause(), []);
  const toggle = useCallback((i: number) => (active === i && playing ? pause() : play(i)), [active, playing, pause, play]);
  const next = useCallback(() => {
    if (active + 1 < clips.length) play(active + 1);
    else pause();
  }, [active, clips.length, play, pause]);

  // Media Session: the lock screen names the show and the publisher, not us.
  useEffect(() => {
    if (!current || typeof navigator === "undefined" || !("mediaSession" in navigator)) return;
    try {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: current.episode_title,
        artist: `${current.show.name} · ${current.show.publisher}`,
        artwork: current.show.art_url ? [{ src: current.show.art_url, sizes: "512x512" }] : [],
      });
      navigator.mediaSession.setActionHandler("play", () => void audio.current?.play());
      navigator.mediaSession.setActionHandler("pause", () => audio.current?.pause());
      navigator.mediaSession.setActionHandler("nexttrack", next);
    } catch {
      /* not every browser accepts every handler */
    }
  }, [current, next]);

  // ← → move between clips while one is active; space is the focused button's own.
  useEffect(() => {
    if (active < 0) return;
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)) return;
      if (e.key === "ArrowRight") {
        e.preventDefault();
        next();
      } else if (e.key === "ArrowLeft" && active > 0) {
        e.preventDefault();
        play(active - 1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, next, play]);

  const onTime = () => {
    const el = audio.current;
    if (!el || !current) return;
    setTime(el.currentTime);
    if (!freeRun && el.currentTime >= current.end_s + shift && !advancing.current) {
      el.pause();
      advancing.current = window.setTimeout(() => {
        advancing.current = null;
        if (active + 1 < clips.length) play(active + 1);
        else setPlaying(false);
      }, ADVANCE_PAUSE_MS);
    }
  };

  const onLoadedMetadata = () => {
    const el = audio.current;
    const i = pendingSeek.current;
    if (!el || i == null) return;
    pendingSeek.current = null;
    const clip = clips[i];
    if (!clip) return;
    seekTo(el, clip);
    void el.play();
  };

  if (!PODCAST_CLIPS || clips.length === 0) return null;

  return (
    <div>
      <audio
        ref={audio}
        preload="none"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onTimeUpdate={onTime}
        onLoadedMetadata={onLoadedMetadata}
      />
      {/* The clips as a rail of compact cards; one transcript window under
          them for the clip that is playing (or the first, until one is). */}
      <ol className="hide-scroll -mx-5 flex snap-x gap-3 overflow-x-auto px-5 pb-1 sm:-mx-8 sm:px-8 lg:mx-0 lg:px-0" aria-label="Podcast clips">
        {clips.map((c, i) => (
          <ClipCard
            key={`${c.audio_url}-${c.start_s}`}
            clip={c}
            active={active === i || (active < 0 && i === 0)}
            playing={active === i && playing}
            progress={active === i ? Math.min(1, Math.max(0, (time - shift - c.start_s) / Math.max(1, c.end_s - c.start_s))) : 0}
            onToggle={() => toggle(i)}
          />
        ))}
      </ol>
      <Transcript
        clip={current ?? clips[0]}
        time={current ? time - shift : null}
        playing={playing}
        freeRun={freeRun && active >= 0}
        onKeepListening={() => {
          setFreeRun(true);
          if (active < 0) play(0);
        }}
      />
      {current && (playing || active >= 0) && (
        <Docked>
          <NowPlaying clip={current} playing={playing} time={time - shift} onToggle={() => toggle(active)} onNext={next} hasNext={active + 1 < clips.length} />
        </Docked>
      )}
    </div>
  );
}

function ClipCard({ clip, active, playing, progress, onToggle }: { clip: ClipOut; active: boolean; playing: boolean; progress: number; onToggle: () => void }) {
  const label = `${playing ? "Pause" : "Play"} the clip from ${clip.show.name}`;
  const secs = Math.max(0, Math.round(clip.end_s - clip.start_s));
  return (
    <li className="clip card flex w-[260px] flex-none snap-start flex-col gap-3 p-3.5 sm:w-[280px]" data-active={active || undefined}>
      <div className="flex items-center gap-2.5">
        <ShowArt show={clip.show} size={40} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13.5px] font-semibold">{clip.show.name}</p>
          <p className="truncate text-[12px]" style={{ color: "var(--ink-3)" }}>{clip.show.publisher} · {relativeTime(clip.published_at)}</p>
        </div>
        <button type="button" onClick={onToggle} aria-label={label} aria-pressed={playing} className="clip-play">
          {playing ? <Pause size={16} /> : <Play size={16} />}
        </button>
      </div>
      <p className="line-clamp-2 text-[14px] leading-[1.45]" style={{ color: "var(--ink-2)" }}>{clip.episode_title}</p>
      <div className="mt-auto flex items-center gap-3">
        <div className="clip-progress flex-1" aria-hidden><span style={{ width: `${progress * 100}%` }} /></div>
        <span className="font-mono text-[11px] tabular-nums" style={{ color: "var(--ink-3)" }}>{mmss(secs)}</span>
      </div>
    </li>
  );
}

/** How long the reader's own scroll keeps the window from following the voice. */
const HANDS_OFF_MS = 4000;

/**
 * The transcript window: the words of the clip in view, a few lines tall,
 * scrolling on its own to keep the word being spoken in the middle — the
 * whole transcript stands in ink and the words already said step back. A
 * reader who scrolls it takes the wheel for a few seconds. Never the whole
 * transcript spilled down the page (founder, 2026-09-21; Particle does this
 * well).
 */
function Transcript({ clip, time, playing, freeRun, onKeepListening }: { clip: ClipOut; time: number | null; playing: boolean; freeRun: boolean; onKeepListening: () => void }) {
  const box = useRef<HTMLDivElement>(null);
  const handsOff = useRef(0);
  const words = clip.words?.length ? clip.words : null;
  const said = time == null || !words ? -1 : words.reduce((k, [, s], i) => (time >= s ? i : k), -1);

  useEffect(() => {
    const el = box.current;
    if (!el || said < 0 || Date.now() < handsOff.current) return;
    const w = el.querySelector<HTMLElement>(`[data-i="${said}"]`);
    if (!w) return;
    const target = w.offsetTop - el.clientHeight / 2 + w.offsetHeight / 2;
    if (Math.abs(el.scrollTop - target) > 8) el.scrollTo({ top: target, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }, [said]);

  return (
    <div className="card mt-3 p-0">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b px-4 py-2.5 text-[12.5px]" style={{ borderColor: "var(--line)", color: "var(--ink-3)" }}>
        <span className="font-semibold" style={{ color: "var(--ink-2)" }}>{clip.show.name}</span>
        <span className="font-mono text-[11px] uppercase tracking-[0.04em]">Transcript {mmss(clip.start_s)}–{mmss(clip.end_s)}</span>
        <span className="ml-auto flex items-center gap-3">
          {clip.episode_url && (
            <a href={clip.episode_url} target="_blank" rel="noopener noreferrer" className="whitespace-nowrap font-semibold underline-offset-4 hover:underline" style={{ color: "var(--ink-2)" }}>Full episode ↗</a>
          )}
          {playing && !freeRun && (
            <button type="button" onClick={onKeepListening} className="whitespace-nowrap font-semibold underline-offset-4 hover:underline" style={{ color: "var(--accent)" }}>Keep listening</button>
          )}
          {freeRun && <span className="whitespace-nowrap">Playing on</span>}
        </span>
      </div>
      <div
        ref={box}
        onWheel={() => { handsOff.current = Date.now() + HANDS_OFF_MS; }}
        onTouchMove={() => { handsOff.current = Date.now() + HANDS_OFF_MS; }}
        className="clip-window max-h-[168px] overflow-y-auto px-4 py-3 text-[16px] leading-[1.7]"
        style={{ color: time != null ? "var(--ink)" : "var(--ink-2)" }}
        aria-live="off"
      >
        {words
          ? words.map(([w], i) => (
              <span key={i} data-i={i} className={i <= said ? "clip-word-said" : "clip-word"}>
                {w}{i < words.length - 1 ? " " : ""}
              </span>
            ))
          : clip.text}
      </div>
    </div>
  );
}

function ShowArt({ show, size }: { show: ClipOut["show"]; size: number }) {
  const [broken, setBroken] = useState(false);
  if (!show.art_url || broken) {
    return (
      <span className="monogram inline-flex items-center justify-center" style={{ width: size, height: size }} aria-hidden>
        <Headphones size={Math.round(size * 0.55)} />
      </span>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={show.art_url} alt="" width={size} height={size} loading="lazy" referrerPolicy="no-referrer" className="rounded-[6px] object-cover" style={{ width: size, height: size }} onError={() => setBroken(true)} />
  );
}

/** The bar that rides above the thumb zone while a clip plays: what is on, pause, next. */
/**
 * Where the bar lives. On a desk the record's foot has a slot (#story-foot-slot,
 * StoryView) that rides the viewport with the Ask bar; the player docks there,
 * above the bar and clear of the Ask drawer, instead of floating over both
 * (founder, 2026-09-21). On the phone, and anywhere without the slot, it stays
 * a fixed bar above the thumb zone.
 */
function Docked({ children }: { children: React.ReactNode }) {
  const [slot, setSlot] = useState<HTMLElement | null>(null);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const find = () => setSlot(mq.matches ? document.getElementById("story-foot-slot") : null);
    find();
    mq.addEventListener("change", find);
    return () => mq.removeEventListener("change", find);
  }, []);
  return slot ? createPortal(<div className="clip-bar-docked">{children}</div>, slot) : <>{children}</>;
}

function NowPlaying({ clip, playing, time, onToggle, onNext, hasNext }: { clip: ClipOut; playing: boolean; time: number; onToggle: () => void; onNext: () => void; hasNext: boolean }) {
  return (
    <div className="clip-bar glass" role="region" aria-label="Now playing">
      <ShowArt show={clip.show} size={32} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-semibold">{clip.show.name} <span className="font-normal" style={{ color: "var(--ink-3)" }}>· {clip.show.publisher}</span></p>
        <p className="truncate font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>{mmss(Math.max(clip.start_s, time))} of {mmss(clip.end_s)} · {clip.episode_title}</p>
      </div>
      <button type="button" onClick={onToggle} className="icon-btn" aria-label={playing ? "Pause" : "Play"}>{playing ? <Pause size={16} /> : <Play size={16} />}</button>
      {hasNext && <button type="button" onClick={onNext} className="icon-btn" aria-label="Next clip"><SkipNext size={16} /></button>}
    </div>
  );
}

/** "Heard on N shows" for a feed row: shows with a clip on the story. */
export function HeardOn({ shows }: { shows?: string[] }) {
  const n = shows?.length ?? 0;
  const label = useMemo(() => (n === 1 ? "Heard on 1 show" : `Heard on ${n} shows`), [n]);
  if (!PODCAST_CLIPS || n === 0) return null;
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap font-mono text-[11px] tracking-[0.02em]" style={{ color: "var(--ink-3)" }}>
      <Headphones size={13} /> {label}
    </span>
  );
}
