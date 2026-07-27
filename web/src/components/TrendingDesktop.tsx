"use client";

import Link from "next/link";

import type { TrendingStory } from "@/lib/api";
import { istDate } from "@/lib/dateline";

// The desktop Trending screen (Parse Desktop.dc.html, TRENDING screen), on the
// same Stone grid as the desktop Feed: a 104px mono ledger rail outside a 1240px
// field of twelve 74px columns with 32px gutters (104 + 32 + 1240 = 1376).
//
// Below lg this renders nothing and the phone's ranked list stands.
//
// What the design asked for that the API cannot answer:
//  - a per-row "moved" clock in the rail. /api/v1/trending returns no timestamp
//    for a story (see api/routes/trending.py), so the rail carries the counted
//    facts it does have instead of a fabricated time.
//  - a velocity number + proportional bar. `velocity` exists (distinct new
//    outlets in 6h) but is 0.0 for every live story, so a whole column of "0"
//    is a dead column. The bar encodes coverage weight — source_count against
//    the widest-covered story, labelled with that exact number above it — and
//    velocity keeps its one honest word, DEVELOPING, in the rail when it moves.

const RAIL = "grid grid-cols-[104px_1240px] gap-x-8";
const FIELD = "grid grid-cols-[repeat(12,74px)] gap-x-8";
const MONO = "font-mono text-[10.5px] uppercase tracking-[0.1em]";

type SectorTab = { slug: string | null; label: string };
type TrendingScope = "region" | "national";

type Props = {
  /** null while the first list is in flight. */
  stories: TrendingStory[] | null;
  scope: TrendingScope;
  onScope: (next: TrendingScope) => void;
  /** The reader's state name (or its code until /regions lands); null = no state. */
  stateName: string | null;
  sector: string | null;
  onSector: (slug: string | null) => void;
  sectors: readonly SectorTab[];
};

function Tab({
  label,
  active,
  onClick,
  small,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  small?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`flex-none whitespace-nowrap pb-1 transition hover:opacity-70 ${small ? "text-[12.5px]" : "text-[13.5px]"}`}
      style={{
        color: active ? "var(--ink)" : "var(--ink-muted)",
        borderBottom: active ? "2px solid var(--ink)" : "2px solid transparent",
      }}
    >
      {label}
    </button>
  );
}

export function TrendingDesktop({
  stories,
  scope,
  onScope,
  stateName,
  sector,
  onSector,
  sectors,
}: Props) {
  // Widest coverage in the list sets the bar's full width, so the column reads
  // as a comparison inside this list rather than an absolute scale.
  const maxSources = Math.max(1, ...(stories ?? []).map((s) => s.source_count));

  return (
    <div className="mx-auto hidden w-[1376px] pb-20 lg:block">
      <div className={`${RAIL} pt-6`}>
        {/* Wraps to two lines inside 104px, which is what the rail is for. */}
        <div className={`${MONO} leading-[1.9]`} style={{ color: "var(--ink-faint)" }}>
          {/* Only once the client fetch has landed: this page prerenders, and a
              build-time dateline would both lie and trip hydration. */}
          {stories !== null && istDate(new Date())}
        </div>
        <div>
          <h1 className="text-[30px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
            Trending
          </h1>
          <div className="mt-4 flex items-center gap-[22px] whitespace-nowrap">
            <div className="flex items-center gap-[22px]" role="group" aria-label="Scope">
              {/* No state, no state tab — a scope the reader cannot use is the
                  bug the phone's sheet already fixed by disabling it there. */}
              {stateName && (
                <Tab label={stateName} active={scope === "region"} onClick={() => onScope("region")} />
              )}
              <Tab label="National" active={scope === "national"} onClick={() => onScope("national")} />
            </div>
            <span className="h-[14px] w-px flex-none" style={{ background: "var(--line)" }} />
            <div className="flex items-center gap-[22px]" role="group" aria-label="Sector">
              {sectors.map((s) => (
                <Tab
                  key={s.label}
                  small
                  label={s.label}
                  active={sector === s.slug}
                  onClick={() => onSector(s.slug)}
                />
              ))}
            </div>
          </div>
          <div className="mt-[18px] border-b" style={{ borderColor: "var(--line)" }} />
        </div>
      </div>

      {stories === null
        ? [0, 1, 2, 3, 4].map((i) => (
            <div key={i} className={RAIL}>
              <div />
              <div className={`${FIELD} h-[88px] items-center border-b`} style={{ borderColor: "var(--line)" }}>
                <div
                  className="h-[15px] animate-pulse"
                  style={{ gridColumn: "2 / span 6", background: "var(--bg-sunken)" }}
                />
              </div>
            </div>
          ))
        : stories.map((s, i) => <Row key={s.slug} story={s} rank={i + 1} maxSources={maxSources} />)}

      {stories !== null && stories.length === 0 && (
        <div className={`${RAIL} pt-7`}>
          <div />
          <p className="text-[13.5px]" style={{ color: "var(--ink-faint)" }}>
            No trending stories here right now — check back soon.
          </p>
        </div>
      )}
    </div>
  );
}

function Row({
  story,
  rank,
  maxSources,
}: {
  story: TrendingStory;
  rank: number;
  maxSources: number;
}) {
  // The storyline's NAME leads, not one outlet's headline — the list and the
  // page it opens have to agree about what the story is called. The headline
  // still shows, beside it: that is what the extra desktop width buys.
  const name = story.label ?? story.hero_title;
  const headline = story.hero_title && story.hero_title !== name ? story.hero_title : null;

  return (
    <div className={RAIL}>
      <div className={`${MONO} pt-[30px] leading-[1.9]`} style={{ color: "var(--ink-faint)" }}>
        <div>
          {story.developments} update{story.developments === 1 ? "" : "s"}
        </div>
        {story.velocity > 0 && <div style={{ color: "var(--up)" }}>developing</div>}
      </div>

      <div className={`${FIELD} h-[88px] items-center border-b`} style={{ borderColor: "var(--line)" }}>
        <div
          className="text-[42px] leading-none"
          style={{ gridColumn: "1 / span 1", fontFamily: "var(--font-display), serif", color: "var(--ink-faint)" }}
        >
          {rank}
        </div>

        <div className="min-w-0" style={{ gridColumn: "2 / span 6" }}>
          {story.sector && (
            <div className={MONO} style={{ color: "var(--ink-muted)" }}>
              {story.sector.replaceAll("_", " ")}
            </div>
          )}
          <Link
            href={`/trending/${story.slug}`}
            className="mt-[5px] block truncate text-[15.5px] leading-[1.35] transition hover:opacity-70"
          >
            {name}
          </Link>
        </div>

        {headline && (
          <p
            className="line-clamp-3 text-[12.5px] leading-[1.4]"
            style={{ gridColumn: "8 / span 3", color: "var(--ink-muted)" }}
          >
            {headline}
          </p>
        )}

        <div style={{ gridColumn: "11 / span 2" }}>
          <div className="font-mono text-[12.5px]" style={{ color: "var(--ink)" }}>
            {story.source_count} source{story.source_count === 1 ? "" : "s"}
          </div>
          <div
            className="mt-1.5 h-[2px]"
            style={{
              background: "var(--ink-faint)",
              width: `${Math.round((story.source_count / maxSources) * 100)}%`,
            }}
          />
        </div>
      </div>
    </div>
  );
}
