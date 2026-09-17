"use client";

import Link from "next/link";
import { Corner } from "@/components/icons";
import { useEffect, useRef, useState } from "react";
import type { StoryTimelineData } from "@/lib/api";
import { shortDate } from "@/lib/dateline";

// "The story so far" — ONE canonical, chronological timeline of a story's
// developments, identical on every development (they share the same connected
// component). Replaces the old per-event "The thread" (causal) + "The story so
// far" (branches): a leaf no longer collapses to a 1-node view, and causal
// rationale now rides inline as a "why" note under the development it explains.
// DESIGN.md: monochrome chrome (no lens hue), IBM Plex Mono for dates
// (provenance), General Sans for titles/cast, hairline rule; reveal-on-scroll
// stagger collapsing to instant under reduced-motion.

function dateLabel(iso: string | null): string {
  return iso ? shortDate(iso) : "";
}

export function StoryTimeline({ story, mode = "timeline" }: { story?: StoryTimelineData; mode?: "timeline" | "related" }) {
  const [shown, setShown] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setShown(true);
      return;
    }
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => e.isIntersecting && setShown(true),
      { rootMargin: "-40px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const developments = story?.developments ?? [];
  const cast = story?.cast ?? [];
  // A timeline only exists when there's more than just this event.
  if (developments.filter((d) => !d.is_current).length === 0) return null;

  if (mode === "related") {
    return (
      <section ref={ref} className="mt-6" aria-labelledby="related-coverage-title">
        <h2 id="related-coverage-title" className="mb-1.5 font-display text-[26px] font-medium uppercase leading-none tracking-[0.03em]">
          Related coverage under review
        </h2>
        <p className="mb-4 max-w-[70ch] text-[12.5px]" style={{ color: "var(--ink-faint)" }}>
          These events share subject or cast signals. Prism has not yet verified that they form one unfolding story, so no chronology or causal path is implied.
        </p>
        <ul className="flex flex-col">
          {developments.map((n, i) => (
            <li
              key={n.id}
              className="rule-live grid grid-cols-[52px_1fr] gap-3 py-3"
              style={{
                opacity: shown ? 1 : 0,
                transform: shown ? "none" : "translateY(6px)",
                transition: "opacity 180ms ease, transform 180ms ease",
                transitionDelay: `${Math.min(i, 8) * 40}ms`,
              }}
            >
              <span className="pt-[3px] font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
                {dateLabel(n.occurred_at)}
              </span>
              {n.is_current ? (
                <span className="text-[14.5px] font-semibold leading-snug">{n.title}</span>
              ) : (
                <Link href={`/story/${n.id}`} className="text-[14.5px] font-medium leading-snug underline-offset-4 hover:underline" style={{ color: "var(--ink-muted)" }}>
                  {n.title}
                </Link>
              )}
            </li>
          ))}
        </ul>
      </section>
    );
  }

  return (
    <section ref={ref} className="mt-11">
      <h2 className="mb-1.5 font-display text-[26px] font-medium uppercase leading-none tracking-[0.03em]">
        The story so far
      </h2>
      <p className="mb-4 text-[12.5px]" style={{ color: "var(--ink-faint)" }}>
        Every development in this story, oldest to latest, with how each followed from the last.
      </p>

      {cast.length > 0 && (
        <div className="mb-6 flex flex-wrap items-center gap-1.5">
          <span
            className="text-[11px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: "var(--ink-faint)" }}
          >
            Following
          </span>
          {cast.map((name) => (
            <span
              key={name}
              className="rounded-full border px-2.5 py-0.5 text-[12px] font-medium"
              style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
            >
              {name}
            </span>
          ))}
        </div>
      )}

      {/* Timeline: a hairline rule down the left, one dated node per development. */}
      <ol className="relative flex flex-col" style={{ marginLeft: 6 }}>
        <span
          aria-hidden
          className="absolute bottom-1 left-0 top-1 w-px"
          style={{ background: "var(--line)" }}
        />
        {developments.map((n, i) => (
          <li
            key={n.id}
            className="relative flex gap-4 py-2.5 pl-6 transition-all"
            style={{
              opacity: shown ? 1 : 0,
              transform: shown ? "none" : "translateY(6px)",
              transitionDelay: `${Math.min(i, 8) * 60}ms`,
            }}
          >
            {/* marker: filled ink = you are here, hollow = other development */}
            <span
              aria-hidden
              className="absolute left-0 top-[15px] h-[9px] w-[9px] -translate-x-1/2 rounded-full"
              style={
                n.is_current
                  ? { background: "var(--ink)", border: "2px solid var(--ink)" }
                  : { background: "var(--bg)", border: "1.5px solid var(--line-strong)" }
              }
            />
            <span
              className="w-[52px] shrink-0 pt-[3px] font-mono text-[11px]"
              style={{ color: "var(--ink-faint)" }}
            >
              {dateLabel(n.occurred_at)}
            </span>
            <span className="flex flex-col gap-0.5">
              {n.is_current ? (
                <>
                  <span
                    className="text-[14.5px] font-semibold leading-snug"
                    style={{ color: "var(--ink)" }}
                  >
                    {n.title}
                  </span>
                  <span
                    className="font-mono text-[9.5px] uppercase tracking-[0.14em]"
                    style={{ color: "var(--ink-faint)" }}
                  >
                    You are here
                  </span>
                </>
              ) : (
                <Link
                  href={`/story/${n.id}`}
                  className="text-[14.5px] font-medium leading-snug"
                  style={{ color: "var(--ink-muted)" }}
                >
                  {n.title}
                </Link>
              )}
              {n.why && (
                <span className="flex items-start gap-1.5 text-[12px] leading-snug" style={{ color: "var(--ink-faint)" }}>
                  <Corner className="mt-[2px] shrink-0" /> {n.why}
                </span>
              )}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
