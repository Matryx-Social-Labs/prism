"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { CoverageBar } from "@/components/Coverage";
import { Masthead } from "@/components/Masthead";
import { SectionHead } from "@/components/SectionHead";
import { SectorStrip } from "@/components/SectorStrip";
import { StatusPill } from "@/components/StatusPill";
import { fetchTrending, type TrendingStory } from "@/lib/api";
import { PhotoStack } from "@/components/PhotoStack";
import { RowListSkeleton } from "@/components/Skeletons";
import { arcHref, isStale, spanDays } from "@/lib/arc";
import { istTime, relativeTime } from "@/lib/dateline";
import { loadProfile } from "@/lib/profile";
import { loadScope, saveScope, type Scope as SharedScope } from "@/lib/scope";
import { sectorGroup, sectorParam } from "@/lib/sectors";
import { useScrollRestore } from "@/lib/useScrollRestore";
import { useStateName } from "@/lib/useStateName";
import { RouteGlyph } from "@/components/RouteGlyph";
import { EmptyState } from "@/components/tabs/EmptyState";

/**
 * Stories: what is developing over days (the URL stays /trending). Rows are
 * stories, not events, on the same row grammar as Today: subject · last moved ·
 * span, the story's name in the record voice, a counted line, then the coverage
 * bar and the verification status. A row opens the record with the route in view.
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
    if (!stories) return undefined;
    const n = stories.length >= LIMIT ? `${LIMIT}+` : String(stories.length);
    // Ranked by new reporting, so the moving ones come first: fewer than a full
    // page is the exact count; a full page of them may hide more ("24+").
    const movingN = stories.filter((s) => s.velocity > 0).length;
    const moving = movingN >= LIMIT ? `${LIMIT}+` : movingN ? String(movingN) : null;
    return `${n} developing ${stories.length === 1 ? "story" : "stories"}${moving ? ` · ${moving} moving now` : ""} · ranked by new reporting`;
  }, [stories]);

  const scopes: [Scope, string][] = [["region", stateName ?? "Your state"], ["national", "National"]];
  const subject = sectorGroup(group)?.name ?? "all sectors";

  return (
    <div className="mx-auto max-w-[var(--shell)] px-[var(--gutter)] pb-[calc(var(--tabbar)+24px)] lg:pb-12">
      <Masthead dateline={clock ? `Stories · ${clock} IST` : "Stories"} />
      <div className="lg:grid lg:grid-cols-[var(--rail)_minmax(0,1fr)] lg:gap-8 lg:pt-6">
        <SectorStrip active={group} onPick={setGroup} allHref="/trending" allLabel="All stories" responsiveRail />
        <div className="grid min-w-0 content-start gap-3 pt-4 lg:pt-0">
          <SectionHead id="stories-title" as="h1" title="Stories" sub={subline} />
          {state && (
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Scope">
              {scopes.map(([s, l]) => (
                <button key={s} onClick={() => pickScope(s)} aria-pressed={scope === s} className="p-chip min-h-8 px-3 text-[13px]">{l}</button>
              ))}
            </div>
          )}
          <section aria-label={`Stories, ${subject}`}>
            {error ? (
              <div className="p-alert p-alert--error" role="status"><p>{error}</p></div>
            ) : stories === null ? (
              <RowListSkeleton n={5} label="Loading stories" />
            ) : stories.length === 0 ? (
              <EmptyState title={`No story is developing in ${subject} right now.`} />
            ) : (
              <ol className="p-print grid gap-2.5">
                {stories.map((s) => <ArcRow key={s.slug} story={s} />)}
              </ol>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

/**
 * One developing story, on the story row grammar (Design System v2 · StoryRow,
 * reader-phone PhoneStories): meta (subject · last moved · span), the story's
 * name, a counted line with who is named, the photo pile on the right; the foot
 * under both — the bar and its count, then whether the chronology is verified
 * or the grouping is still under review (fail-closed: a provisional route is
 * never drawn as one). Single-outlet rows are dashed, stale ones half-weight.
 */
function ArcRow({ story }: { story: TrendingStory }) {
  const single = story.source_count <= 1;
  const stale = isStale(story);
  const span = spanDays(story);
  const verified = story.boundary_status === "verified";
  const group = sectorGroup(story.sector);
  const memberLabel = verified
    ? `${story.developments} ${story.developments === 1 ? "development" : "developments"}`
    : `${story.developments} related ${story.developments === 1 ? "report" : "reports"}`;
  const outlets = `${story.source_count} ${story.source_count === 1 ? "outlet" : "outlets"}`;
  const cast = story.cast?.length ? story.cast.slice(0, 4).join(", ") : null;
  const moved = story.velocity > 0 ? "moving now" : story.last_updated_at ? `moved ${relativeTime(story.last_updated_at)}` : null;
  const clockLine = [moved, span != null && span > 0 ? `${span} ${span === 1 ? "day" : "days"}` : null].filter(Boolean).join(" · ");

  return (
    <li>
      <Link
        href={arcHref(story)}
        className={`p-row group ${single ? "p-row--single" : ""} ${stale ? "p-row--stale" : ""}`}
        style={{ padding: "14px 16px", gap: 8 }}
      >
        <div className="flex items-start gap-3">
          <div className="grid min-w-0 flex-1 gap-1.5">
            <div className="p-meta">
              {group && <span className="p-meta__subject">{group.name}</span>}
              {group && clockLine && <span className="p-meta__sep" />}
              {clockLine && <span className="p-meta__prov">{clockLine}</span>}
            </div>
            <h2 className="p-row__title">{story.label ?? story.hero_title}</h2>
            <p className="p-row__sum">{memberLabel} across {outlets}.{cast ? ` Named: ${cast}.` : ""}</p>
            <RouteGlyph route={verified ? story.route : null} />
          </div>
          {story.photos?.length ? <PhotoStack photos={story.photos} /> : null}
        </div>
        {/* The foot wraps under the whole card: a pill that cannot shrink beside
            the pile widened the page on a phone (2026-09-21). The list API has
            no origin split, so the bar is drawn neutral; its count is the legend. */}
        <div className="p-row__foot">
          <span className="inline-flex min-w-0 items-center gap-2.5">
            <CoverageBar outlets={[]} fallbackCount={story.source_count} className="p-covbar--mono" />
            <span className="p-count">{outlets} · {story.developments} {story.developments === 1 ? "report" : "reports"}</span>
          </span>
          <span className="ml-auto">
            {verified ? <StatusPill status="verified" /> : <StatusPill status="provisional" label="Grouping under review" />}
          </span>
        </div>
      </Link>
    </li>
  );
}
