"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { EntityOut } from "@/lib/api";

// "The story so far" — a monochrome, chronological timeline of a story's
// developments (branches), linked by the actors it follows. DESIGN.md: chrome is
// monochrome (no lens hue here), IBM Plex Mono for dates (provenance), General
// Sans for titles/cast, hairline rule. Reveal-on-scroll stagger; reduced-motion
// collapses to instant.

interface Development {
  id: string;
  title: string;
  last_updated_at: string;
}

function dateLabel(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

export function StoryTrail({
  currentId,
  currentTitle,
  currentUpdatedAt,
  related,
  entities,
}: {
  currentId: string;
  currentTitle: string;
  currentUpdatedAt: string;
  related: Development[];
  entities: EntityOut[];
}) {
  // The cast: the story's recurring actors (people/organizations), not places.
  const cast = entities
    .filter((e) => e.entity_type === "person" || e.entity_type === "organization")
    .slice(0, 5);

  // The trail: branches + this article, oldest → newest, so the arc reads in order.
  const nodes = [
    ...related.map((r) => ({ ...r, current: false })),
    { id: currentId, title: currentTitle, last_updated_at: currentUpdatedAt, current: true },
  ].sort((a, b) => +new Date(a.last_updated_at) - +new Date(b.last_updated_at));

  const [shown, setShown] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
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

  if (related.length === 0) return null;

  return (
    <section ref={ref} className="mt-11">
      <h2 className="mb-1.5 text-[23px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
        The story so far
      </h2>
      <p className="mb-4 text-[12.5px]" style={{ color: "var(--ink-faint)" }}>
        Every development in this story, oldest to latest — linked by the people and parties it follows.
      </p>

      {cast.length > 0 && (
        <div className="mb-6 flex flex-wrap items-center gap-1.5">
          <span className="text-[10.5px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
            Following
          </span>
          {cast.map((c) => (
            <span
              key={c.name}
              className="rounded-full border px-2.5 py-0.5 text-[12px] font-medium"
              style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
            >
              {c.name}
            </span>
          ))}
        </div>
      )}

      {/* Timeline: a hairline rule down the left, one dated node per development. */}
      <ol className="relative flex flex-col" style={{ marginLeft: 6 }}>
        <span aria-hidden className="absolute bottom-1 left-0 top-1 w-px" style={{ background: "var(--line)" }} />
        {nodes.map((n, i) => (
          <li
            key={n.id}
            className="relative flex gap-4 py-2.5 pl-6 transition-all"
            style={{
              opacity: shown ? 1 : 0,
              transform: shown ? "none" : "translateY(6px)",
              transitionDelay: `${Math.min(i, 8) * 60}ms`,
            }}
          >
            {/* marker on the rule: filled ink = you are here, hollow = other */}
            <span
              aria-hidden
              className="absolute left-0 top-[15px] h-[9px] w-[9px] -translate-x-1/2 rounded-full"
              style={
                n.current
                  ? { background: "var(--ink)", border: "2px solid var(--ink)" }
                  : { background: "var(--bg)", border: "1.5px solid var(--line-strong)" }
              }
            />
            <span className="w-[52px] shrink-0 pt-[3px] font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
              {dateLabel(n.last_updated_at)}
            </span>
            {n.current ? (
              <span className="flex flex-col gap-0.5">
                <span className="text-[14.5px] font-semibold leading-snug" style={{ color: "var(--ink)" }}>
                  {n.title}
                </span>
                <span className="font-mono text-[9.5px] uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
                  You are here
                </span>
              </span>
            ) : (
              <Link href={`/story/${n.id}`} className="text-[14.5px] font-medium leading-snug" style={{ color: "var(--ink-muted)" }}>
                {n.title}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
