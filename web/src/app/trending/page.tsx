"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Masthead } from "@/components/Masthead";
import { SectorStrip } from "@/components/SectorStrip";
import { fetchTrending, type TrendingStory } from "@/lib/api";
import { arcHref, isStale, spanDays } from "@/lib/arc";
import { istDate, shortDate } from "@/lib/dateline";
import { loadProfile } from "@/lib/profile";
import { loadScope, saveScope, type Scope as SharedScope } from "@/lib/scope";
import { sectorCode, sectorGroup, sectorParam } from "@/lib/sectors";
import { useScrollRestore } from "@/lib/useScrollRestore";
import { useStateName } from "@/lib/useStateName";
import { RouteGlyph } from "@/components/RouteGlyph";

/**
 * Trending: the chart of arcs (shape brief §4). Rows are stories, not events;
 * the number at the left is how many developments the arc has, and the label
 * grid beneath prints OUTLETS · MOVED · SPAN · CODE. Scope and the sector strip
 * are the front page's. A row opens the ticket with the route in view.
 *
 * Trending has no "all" tier — National IS everything here — so the shared
 * scope is narrowed at this one call site, and writing it back never narrows
 * what the Feed saved (an "all" there stays "all").
 */
type Scope = Extract<SharedScope, "region" | "national">;

export default function TrendingPage() {
  const [state, setState] = useState<string | null>(null);
  const [scope, setScope] = useState<Scope>("national");
  const [group, setGroup] = useState<string | null>(null);
  const [stories, setStories] = useState<TrendingStory[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  // The profile is a client-only read: wait for it rather than fetch national
  // and then again scoped.
  const [ready, setReady] = useState(false);
  const stateName = useStateName(state);

  useEffect(() => {
    const p = loadProfile();
    if (p?.state) setState(p.state);
    const saved = loadScope(Boolean(p?.state));
    if (saved) setScope(saved === "region" ? "region" : "national");
    else if (p?.state) setScope("region");
    setReady(true);
  }, []);

  const pickScope = (next: Scope) => {
    setScope(next);
    saveScope(next === "national" && loadScope() === "all" ? "all" : next);
  };

  useEffect(() => {
    if (!ready) return;
    setStories(null);
    setError(null);
    let cancelled = false;
    const g = sectorGroup(group);
    fetchTrending({ state: scope === "region" ? state : null, sector: g ? sectorParam(g) : null, limit: 24 })
      .then((s) => { if (!cancelled) setStories(s); })
      .catch(() => { if (!cancelled) setError("The Prism API is unreachable right now."); });
    return () => { cancelled = true; };
  }, [scope, state, group, ready]);

  useScrollRestore("trending:scrollY", stories !== null);

  const dateline = useMemo(() => {
    const d = istDate(new Date());
    if (!stories) return d;
    const moving = stories.filter((s) => s.velocity > 0).length;
    return `${d} · ${stories.length} ${stories.length === 1 ? "story" : "stories"}${moving ? ` · ${moving} moving` : ""}`;
  }, [stories]);

  const scopes: [Scope, string][] = [["region", stateName ?? "Your state"], ["national", "National"]];
  const subject = sectorGroup(group)?.name ?? "all sectors";

  return (
    <div className="mx-auto max-w-[1240px] px-5 pb-24 sm:px-8 lg:pb-16">
      <Masthead dateline={dateline} right={state ? (
        <div className="flex gap-3 font-mono text-[11px] uppercase tracking-[0.06em]">
          {scopes.map(([s, l]) => (
            <button key={s} onClick={() => pickScope(s)} aria-pressed={scope === s}
              className="underline-offset-4 aria-pressed:underline"
              style={{ color: scope === s ? "var(--ink)" : "var(--ink-faint)" }}>{l}</button>
          ))}
        </div>
      ) : null} />
      <SectorStrip active={group} onPick={setGroup} allLabel="" />
      <h1 className="pt-4 font-display text-[26px] uppercase leading-none tracking-[0.03em]">Trending</h1>
      <section aria-label={`Trending, ${subject}`} className="pt-3">
        {error ? (
          <p className="rule-live py-6 text-[14.5px]" style={{ color: "var(--danger)" }}>{error}</p>
        ) : stories === null ? (
          <p className="rule-live py-6 font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-faint)" }}>Printing…</p>
        ) : stories.length === 0 ? (
          <p className="rule-live py-8 text-[15px]" style={{ color: "var(--ink-muted)" }}>No story is moving in {subject} right now.</p>
        ) : (
          <ol className="chart-print">
            {stories.map((s, i) => <ArcRow key={s.slug} story={s} lead={i === 0} />)}
          </ol>
        )}
      </section>
    </div>
  );
}

/**
 * One arc on the chart. Same grammar as a chart row: the count at the left is
 * the row's weight (developments here, not outlets), the story's NAME in the
 * reading voice (the cast we generated, so the row and the page agree on what
 * the story is called), then the label grid in mono. State is line form: a
 * single-outlet arc sits on a dashed rule; one that has not moved in three
 * days prints at half weight. No thumbnail: the chart has no pictures in its
 * rows, and a 56px crop of one outlet's photo said nothing about an arc.
 */
function ArcRow({ story, lead = false }: { story: TrendingStory; lead?: boolean }) {
  const single = story.source_count <= 1;
  const stale = isStale(story);
  const rule = single ? "rule-single" : stale ? "rule-stale" : "rule-live";
  const span = spanDays(story);
  // The count column is developments here, not outlets as on the chart, so
  // the grid says so first; "moving" replaces the last-moved date rather
  // than joining it.
  const verified = story.boundary_status === "verified";
  const memberLabel = verified
    ? `${story.developments} ${story.developments === 1 ? "development" : "developments"}`
    : `${story.developments} related ${story.developments === 1 ? "event" : "events"}`;
  const grid = [
    memberLabel,
    `${story.source_count} ${story.source_count === 1 ? "outlet" : "outlets"}`,
    story.velocity > 0 ? null : story.last_updated_at ? `moved ${shortDate(story.last_updated_at)}` : null,
    span != null ? `span ${span}d` : null,
    sectorCode(story.sector) || null,
  ].filter((x): x is string => Boolean(x));

  return (
    <li className={rule}>
      <Link
        href={arcHref(story)}
        className={`group grid gap-x-4 ${lead ? "grid-cols-[56px_1fr] py-5" : "grid-cols-[40px_1fr] py-3.5"} focus-visible:outline-none`}
      >
        <span
          className={`${lead ? "font-display text-[44px] leading-[0.9] tracking-[-0.01em]" : "font-mono text-[13px] leading-[1.9]"} tabular-nums text-right`}
          style={{ color: single ? "var(--ink-faint)" : "var(--ink)" }}
          aria-label={memberLabel}
        >
          {story.developments}
        </span>
        <div className="min-w-0">
          <h2
            className={`${lead ? "text-[22px] leading-[1.25] sm:text-[26px]" : "text-[15.5px] leading-[1.4]"} font-medium text-balance group-hover:underline group-focus-visible:underline underline-offset-4`}
            style={{ color: "var(--ink)" }}
          >
            {story.label ?? story.hero_title}
          </h2>
          <RouteGlyph route={verified ? story.route : null} />
          <div
            className="mt-1.5 flex flex-wrap items-baseline gap-x-2.5 font-mono text-[11px] uppercase tracking-[0.04em]"
            style={{ color: "var(--ink-faint)" }}
          >
            {story.velocity > 0 && <span style={{ color: "var(--ink)" }}>moving</span>}
            {grid.map((g) => <span key={g}>{g}</span>)}
          </div>
        </div>
      </Link>
    </li>
  );
}
