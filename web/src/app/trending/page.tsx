"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { CoverageBar } from "@/components/Coverage";
import { Masthead } from "@/components/Masthead";
import { SectionHead } from "@/components/SectionHead";
import { SectorStrip } from "@/components/SectorStrip";
import { StatusPill } from "@/components/StatusPill";
import { fetchTrending, type TrendingStory } from "@/lib/api";
import { arcHref, isStale, spanDays } from "@/lib/arc";
import { relativeTime } from "@/lib/dateline";
import { loadProfile } from "@/lib/profile";
import { loadScope, saveScope, type Scope as SharedScope } from "@/lib/scope";
import { sectorGroup, sectorParam } from "@/lib/sectors";
import { useScrollRestore } from "@/lib/useScrollRestore";
import { useStateName } from "@/lib/useStateName";
import { RouteGlyph } from "@/components/RouteGlyph";

/**
 * Stories: what is developing over days (the URL stays /trending). Rows are
 * stories, not events, on the same row grammar as Today: subject · last moved ·
 * span, the story's name in the record voice, a counted line, then the coverage
 * bar and the verification status. A row opens the record with the route in view.
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
    const day = new Date().toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", timeZone: "Asia/Kolkata" });
    return day;
  }, []);
  const subline = useMemo(() => {
    if (!stories) return undefined;
    const moving = stories.filter((s) => s.velocity > 0).length;
    return `${stories.length} developing ${stories.length === 1 ? "story" : "stories"}${moving ? ` · ${moving} moving now` : ""} · ranked by new reporting`;
  }, [stories]);

  const scopes: [Scope, string][] = [["region", stateName ?? "Your state"], ["national", "National"]];
  const subject = sectorGroup(group)?.name ?? "all sectors";

  return (
    <div className="mx-auto max-w-[var(--shell)] px-5 pb-[calc(var(--tabbar)+24px)] sm:px-8 lg:pb-16 xl:px-10">
      <Masthead dateline={dateline} />
      <div className="lg:grid lg:grid-cols-[var(--rail)_minmax(0,1fr)] lg:gap-10 lg:pt-6">
        <SectorStrip active={group} onPick={setGroup} allHref="/trending" allLabel="All stories" responsiveRail />
        <div className="min-w-0">
          {state && (
            <div className="flex gap-2 pt-2 lg:pt-0" role="group" aria-label="Scope">
              {scopes.map(([s, l]) => (
                <button key={s} onClick={() => pickScope(s)} aria-pressed={scope === s} className="chip h-8 px-3 text-[13px]">{l}</button>
              ))}
            </div>
          )}
          <SectionHead id="stories-title" title="Stories" hint={subline} />
          <section aria-label={`Stories, ${subject}`}>
            {error ? (
              <div className="card" role="status"><p className="text-[15px] font-medium" style={{ color: "var(--danger)" }}>{error}</p></div>
            ) : stories === null ? (
              <div className="flex flex-col gap-3" aria-busy="true" aria-label="Loading stories">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="row-card px-4 py-4" aria-hidden>
                    <span className="pulse-skel block h-2.5 w-24 rounded" style={{ background: "var(--sunken)" }} />
                    <span className="pulse-skel mt-3 block h-4 rounded" style={{ background: "var(--sunken)", width: ["76%", "64%", "70%"][i] }} />
                    <span className="pulse-skel mt-4 block h-1.5 w-20 rounded" style={{ background: "var(--sunken)" }} />
                  </div>
                ))}
              </div>
            ) : stories.length === 0 ? (
              <div className="card py-8 text-center"><p className="text-[15px]" style={{ color: "var(--ink-2)" }}>No story is developing in {subject} right now.</p></div>
            ) : (
              <ol className="chart-print flex flex-col gap-3">
                {stories.map((s, i) => <ArcRow key={s.slug} story={s} lead={i === 0} />)}
              </ol>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

/**
 * One developing story, on the story row grammar. The counted line says what
 * the row is made of — developments and outlets — and the status pill says
 * whether the chronology is verified or the grouping is still under review
 * (fail-closed: a provisional route is never drawn as one).
 */
function ArcRow({ story, lead = false }: { story: TrendingStory; lead?: boolean }) {
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

  return (
    <li>
      <Link href={arcHref(story)} className={`row-card group ${single ? "single" : ""} ${lead ? "px-[18px] py-5" : "px-4 py-3.5"}`} style={stale ? { opacity: 0.75 } : undefined}>
        <div className="meta-line">
          {group && <span style={{ color: "var(--ink-2)", fontWeight: 500 }}>{group.name}</span>}
          {group && <span className="dot" />}
          {story.velocity > 0 ? (
            <span style={{ color: "var(--accent)", fontWeight: 600 }}>moving now</span>
          ) : story.last_updated_at ? (
            <span>moved {relativeTime(story.last_updated_at)}</span>
          ) : null}
          {span != null && span > 0 && (
            <>
              <span className="dot" />
              <span>{span} {span === 1 ? "day" : "days"}</span>
            </>
          )}
        </div>
        <h2
          className={`font-record font-medium text-balance ${lead ? "mt-2 text-[26px] leading-[1.18] sm:text-[30px]" : "mt-1.5 text-[19px] leading-[1.3]"} group-hover:underline group-focus-visible:underline underline-offset-4 decoration-1`}
          style={{ color: "var(--ink)", letterSpacing: "-0.005em" }}
        >
          {story.label ?? story.hero_title}
        </h2>
        <p className="mt-1 text-[14.5px] leading-[1.5]" style={{ color: "var(--ink-2)" }}>
          {memberLabel} across {outlets}.{cast ? ` Named: ${cast}.` : ""}
        </p>
        <RouteGlyph route={verified ? story.route : null} />
        <div className="mt-3 flex min-w-0 items-center gap-3">
          <span className="inline-flex min-w-0 items-center gap-2.5">
            <CoverageBar outlets={[]} fallbackCount={story.source_count} />
            <span className="truncate font-mono text-[11px] tracking-[0.02em]" style={{ color: "var(--ink-3)" }}>
              {outlets} · {story.developments} {story.developments === 1 ? "report" : "reports"}
            </span>
          </span>
          <span className="flex-1" />
          <StatusPill status={verified ? "verified" : "provisional"} label={verified ? "Verified" : "Grouping under review"} />
        </div>
      </Link>
    </li>
  );
}
