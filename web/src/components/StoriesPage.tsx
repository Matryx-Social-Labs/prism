"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { CoverageBar } from "@/components/Coverage";
import { Masthead } from "@/components/Masthead";
import { SectorStrip } from "@/components/SectorStrip";
import { StatusPill } from "@/components/StatusPill";
import { Alert, EmptyState } from "@/components/ui";
import { fetchTrending, type TrendingStory } from "@/lib/api";
import { arcHref, isStale, spanDays } from "@/lib/arc";
import { Ago } from "@/components/Ago";
import { istTime } from "@/lib/dateline";
import { loadProfile } from "@/lib/profile";
import { loadScope, saveScope, type Scope as SharedScope } from "@/lib/scope";
import { sectorGroup, sectorParam } from "@/lib/sectors";
import { useScrollRestore } from "@/lib/useScrollRestore";
import { useStateName } from "@/lib/useStateName";

/**
 * Stories: what is developing over days (the URL stays /trending). Design
 * System v2 · Reading board, flow 01: a title and one line on what the page
 * is, the subject chips (no counts: the list is one capped page), then one
 * ArcRow per story — status, subject · span · last update, the story's name in
 * the record voice, and a bar in one ink with its counts. The list API carries
 * no outlet-origin split, so the bar cannot be split by origin; the page says
 * so under the list rather than draw a split it does not know.
 *
 * Trending has no "all" tier — National IS everything here — so the shared
 * scope is narrowed at this one call site, and writing it back never narrows
 * what the Feed saved (an "all" there stays "all").
 *
 * `initial` is the national list the server fetched (app/trending/page.tsx),
 * so the stories are in the HTML for crawlers; a reader whose scope is their
 * state re-fetches once the profile is read.
 */
type Scope = Extract<SharedScope, "region" | "national">;

/** The API serves a ranked page, not the whole set: a full page prints "24+". */
const LIMIT = 24;

export function StoriesPage({ initial = null }: { initial?: TrendingStory[] | null }) {
  const [state, setState] = useState<string | null>(null);
  const [scope, setScope] = useState<Scope>("national");
  const [group, setGroup] = useState<string | null>(null);
  const [stories, setStories] = useState<TrendingStory[] | null>(initial);
  const seeded = useRef(initial !== null);
  const [error, setError] = useState<string | null>(null);
  // The profile is a client-only read: wait for it rather than fetch national
  // and then again scoped.
  const [ready, setReady] = useState(false);
  // The masthead's clock is the reader's, read after mount: the server's would
  // be minutes stale in the cached HTML and would not hydrate.
  const [clock, setClock] = useState<string | null>(null);
  const stateName = useStateName(state);

  useEffect(() => {
    const p = loadProfile();
    if (p?.state) setState(p.state);
    const saved = loadScope(Boolean(p?.state));
    if (saved) setScope(saved === "region" ? "region" : "national");
    else if (p?.state) setScope("region");
    setReady(true);
    setClock(istTime(new Date().toISOString()));
  }, []);

  const pickScope = (next: Scope) => {
    setScope(next);
    saveScope(next === "national" && loadScope() === "all" ? "all" : next);
  };

  useEffect(() => {
    if (!ready) return;
    if (seeded.current) {
      seeded.current = false;
      if (scope === "national" && !group) return;
    }
    setStories(null);
    setError(null);
    let cancelled = false;
    const g = sectorGroup(group);
    fetchTrending({ state: scope === "region" ? state : null, sector: g ? sectorParam(g) : null, limit: LIMIT })
      .then((s) => { if (!cancelled) setStories(s); })
      .catch(() => { if (!cancelled) setError("The Prism API is unreachable right now."); });
    return () => { cancelled = true; };
  }, [scope, state, group, ready]);

  useScrollRestore("trending:scrollY", stories !== null);

  // Only what the API gives: how many came back (a full page is "24+", the
  // list is capped), how many gained a new outlet in the last six hours, and
  // the order the API ranks them in.
  const subline = useMemo(() => {
    if (!stories?.length) return undefined;
    const n = stories.length >= LIMIT ? `${LIMIT}+` : String(stories.length);
    // Ranked by new reporting, so the moving ones come first: fewer than a full
    // page is the exact count; a full page of them may hide more ("24+").
    const movingN = stories.filter((s) => s.velocity > 0).length;
    const moving = movingN >= LIMIT ? `${LIMIT}+` : movingN ? String(movingN) : null;
    return `${n} developing ${stories.length === 1 ? "story" : "stories"}${moving ? ` · ${moving} moving now` : ""} · ranked by new reporting`;
  }, [stories]);

  const scopes: [Scope, string][] = [["region", stateName ?? "Your state"], ["national", "National"]];
  const subject = sectorGroup(group)?.name ?? null;

  return (
    <div className="mx-auto max-w-[760px] px-[var(--gutter)] pb-[calc(var(--tabbar)+24px)] lg:pb-16">
      <Masthead dateline={clock ? `Stories · ${clock} IST` : "Stories"} />
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4 pt-4 lg:gap-5 lg:pt-8">
        <div className="grid gap-2">
          <h1 id="stories-title" className="[font:var(--t-display-m)] lg:[font:var(--t-display-l)]" style={{ letterSpacing: "var(--track-display)", textWrap: "balance" }}>
            Developing stories
          </h1>
          <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
            Stories that run over days, each with its developments in order. Provisional groupings say so.
          </p>
        </div>
        {state && (
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Scope">
            {scopes.map(([s, l]) => (
              <button key={s} onClick={() => pickScope(s)} aria-pressed={scope === s} className="p-chip">{l}</button>
            ))}
          </div>
        )}
        <SectorStrip active={group} onPick={setGroup} allHref="/trending" allLabel="All stories" />
        <section aria-labelledby="stories-title" className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-1">
          {error ? (
            <Alert tone="error">{error}</Alert>
          ) : stories === null ? (
            <ArcListSkeleton />
          ) : stories.length === 0 ? (
            <EmptyState
              title={subject ? `No developing ${subject} stories right now` : "No developing stories right now"}
              action={subject ? <button type="button" onClick={() => setGroup(null)} className="p-link inline-flex min-h-11 items-center">All subjects →</button> : undefined}
            >
              A story appears here once two or more outlets have reported two or more developments.
            </EmptyState>
          ) : (
            <>
              {subline && <p className="p-count whitespace-normal">{subline}</p>}
              <ol className="p-print">
                {stories.map((s) => <ArcRow key={s.slug} story={s} />)}
              </ol>
            </>
          )}
        </section>
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
          Coverage bars are drawn in one ink until the list carries the outlet-origin split.
        </p>
      </div>
    </div>
  );
}

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/**
 * One developing story (Reading board · ArcRow): the status first — verified,
 * or a provisional grouping that says so — then subject · span · last update,
 * the story's name, and the one-ink bar labelled with its counts. State is line
 * form: a single-outlet story sits on a dashed rule, one that has not moved in
 * three days at reduced weight. Verified arcs open on their hero's route;
 * provisional groups open on the group page (lib/arc).
 */
function ArcRow({ story }: { story: TrendingStory }) {
  const verified = story.boundary_status === "verified";
  const single = story.source_count <= 1;
  const stale = isStale(story);
  const span = spanDays(story);
  const group = sectorGroup(story.sector);
  // "updated 11h ago" goes through <Ago>: this page is prerendered, so the
  // server's relative time and the reader's legitimately differ (React #418).
  const prov: React.ReactNode[] = [
    span ? plural(span, "day", "days") : null,
    story.last_updated_at ? <>updated <Ago iso={story.last_updated_at} /></> : null,
  ].filter(Boolean);
  const parts = [...(group ? [{ key: "s", subject: true, text: group.name }] : []), ...prov.map((t, i) => ({ key: `p${i}`, subject: false, text: t }))];

  return (
    <li>
      <Link
        href={arcHref(story)}
        className={`group grid gap-2 border-b py-4 ${single ? "p-row--single" : ""} ${stale ? "p-row--stale" : ""}`}
        style={{ borderColor: single ? "var(--line-strong)" : "var(--line)", color: "var(--ink)" }}
      >
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill status={verified ? "verified" : "provisional"} label={verified ? "Verified" : "Provisional grouping"} />
          {parts.length > 0 && (
            <span className="p-meta">
              {parts.map((p, i) => (
                <span key={p.key} className="contents">
                  {i > 0 && <span className="p-meta__sep" />}
                  <span className={p.subject ? "p-meta__subject" : "p-meta__prov"}>{p.text}</span>
                </span>
              ))}
            </span>
          )}
        </div>
        <h2 className="text-balance group-hover:underline" style={{ font: "var(--t-title)", textUnderlineOffset: 4, textDecorationThickness: 1 }}>
          {story.label ?? story.hero_title}
        </h2>
        <span className="flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-1.5">
          <CoverageBar outlets={[]} fallbackCount={story.source_count} width={200} className="p-covbar--mono max-w-full" />
          <span className="p-count">
            {plural(story.developments, "development", "developments")} · {plural(story.source_count, "outlet", "outlets")}
          </span>
        </span>
      </Link>
    </li>
  );
}

/** The list's own shape while it loads: pill and meta, a title line, the bar. */
function ArcListSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading stories">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="grid gap-2.5 border-b py-4" style={{ borderColor: "var(--line)" }}>
          <span className="p-skel h-5 w-40" />
          <span className="p-skel h-5 w-[80%]" />
          <span className="p-skel h-2 w-[200px] max-w-full" />
        </div>
      ))}
    </div>
  );
}
