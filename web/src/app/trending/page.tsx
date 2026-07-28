"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ScopeSheet } from "@/components/ScopeSheet";
import { TrendingDesktop } from "@/components/TrendingDesktop";
import { fetchTrending, type TrendingStory } from "@/lib/api";
import { loadProfile } from "@/lib/profile";
import { loadScope, saveScope, type Scope as SharedScope } from "@/lib/scope";
import { THUMB_W, thumbUrl } from "@/lib/thumb";
import { useScrollRestore } from "@/lib/useScrollRestore";
import { useStateName } from "@/lib/useStateName";

// Trending has no "all" tier — National IS everything here. Narrowed from the
// shared union so adding a member forces a decision at this call site.
type Scope = Extract<SharedScope, "region" | "national">;
const SECTORS = [
  { slug: null as string | null, label: "All sectors" },
  { slug: "politics", label: "Politics" },
  // "finance", not "markets": the API filters on the taxonomy sector slug
  // (common/taxonomy.py), where markets is a SUBSECTOR of finance — so
  // sector=markets matched nothing and the chip was a dead end.
  { slug: "finance", label: "Markets" },
  // No Cyber chip: correlation/trending.py excludes cybersecurity from trending
  // candidates entirely, so that chip could never return a story.
  { slug: "health", label: "Health" },
];

export default function TrendingPage() {
  const [state, setState] = useState<string | null>(null);
  const [scope, setScope] = useState<Scope>("national");
  const [scopeOpen, setScopeOpen] = useState(false);
  const [sector, setSector] = useState<string | null>(null);
  const [stories, setStories] = useState<TrendingStory[] | null>(null);
  // Same gate as the Feed: the profile is a client-only localStorage read, so the
  // first render sees null and the fetch below would fire once national and again
  // scoped. Wait for it instead of paying for a throwaway round trip.
  const [profileLoaded, setProfileLoaded] = useState(false);
  const stateName = useStateName(state);

  useEffect(() => {
    const p = loadProfile();
    if (p?.state) setState(p.state);
    // Honour the scope the reader chose on the Feed — the sheet says it applies
    // everywhere, so it has to. Trending has no "all" tier, so the everything
    // choice lands on its closest equivalent (national).
    const saved = loadScope(Boolean(p?.state));
    if (saved) setScope(saved === "region" ? "region" : "national");
    else if (p?.state) setScope("region");
    setProfileLoaded(true);
  }, []);

  const chooseScope = (next: Scope) => {
    setScope(next);
    // Trending only speaks two tiers, the Feed speaks three. Writing "national"
    // back over a Feed-saved "all" silently narrowed it: on the Feed "all" is
    // everything, while "national" EXCLUDES the reader's own state — so tapping
    // National here quietly hid their state's news over there, which they never
    // asked for. Both render as National on this page, so keeping the wider
    // value is invisible here and lossless there.
    saveScope(next === "national" && loadScope() === "all" ? "all" : next);
  };

  useEffect(() => {
    if (!profileLoaded) return;
    setStories(null);
    // Mount fires world-scope then region-scope once the profile loads; if the
    // first lands last the list disagrees with the scope chip above it.
    let cancelled = false;
    fetchTrending({ state: scope === "region" ? state : null, sector, limit: 24 })
      .then((s) => {
        if (!cancelled) setStories(s);
      })
      .catch(() => {
        if (!cancelled) setStories([]);
      });
    return () => {
      cancelled = true;
    };
  }, [scope, state, sector, profileLoaded]);

  useScrollRestore("trending:scrollY", stories !== null);

  const scopeLabel = scope === "region" ? stateName ?? "Your state" : "National";
  const scopeOpts: [Scope, string][] = useMemo(
    () => [
      ["region", stateName ? `Your state — ${stateName}` : "Your state"],
      ["national", "National"],
    ],
    [stateName],
  );

  return (
    // Same Stone grid + same regression fix as the feed: this was
    // max-w-[620px] with no breakpoint.
    <div className="relative mx-auto max-w-[620px] pb-28 lg:max-w-[1376px] lg:pb-20">
      {/* Desktop gets its own composition — a ruled ledger of ranked storylines
          with the evidence in the margin (Prism Desktop.dc.html). Everything
          below it is the phone's, and stays the phone's. */}
      <TrendingDesktop
        stories={stories}
        scope={scope}
        onScope={chooseScope}
        stateName={stateName}
        sector={sector}
        onSector={setSector}
        sectors={SECTORS}
      />

      <div className="lg:hidden">
      <div
        className="sticky top-0 z-20 flex items-center gap-2.5 border-b px-5 py-2.5 backdrop-blur-md"
        style={{ borderColor: "var(--line)", background: "var(--glass)" }}
      >
        <h1 className="text-[19px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
          Trending
        </h1>
        <button
          onClick={() => setScopeOpen(true)}
          className="ml-auto inline-flex h-11 items-center gap-1.5 rounded-full border px-3.5 text-[12.5px] font-semibold"
          style={{ borderColor: "var(--line-strong)", background: "var(--bg-elevated)", color: "var(--ink)" }}
        >
          ◉ {scopeLabel} <span style={{ color: "var(--ink-faint)" }}>▾</span>
        </button>
      </div>

      {/* sector chips */}
      <div className="hide-scroll flex gap-2 overflow-x-auto border-b px-5 py-2.5" style={{ borderColor: "var(--line)" }}>
        {SECTORS.map((s) => {
          const active = sector === s.slug;
          return (
            <button
              key={s.label}
              onClick={() => setSector(s.slug)}
              className="flex-none whitespace-nowrap rounded-full px-3.5 py-1.5 text-[12px] font-semibold"
              style={active ? { background: "var(--ink)", color: "var(--bg)" } : { border: "1px solid var(--line-strong)", color: "var(--ink-muted)" }}
            >
              {s.label}
            </button>
          );
        })}
      </div>

      <div className="flex flex-col">
        {stories === null ? (
          [0, 1, 2, 3, 4].map((i) => <SkeletonRow key={i} />)
        ) : stories.length === 0 ? (
          <p className="px-5 py-5 text-[13px]" style={{ color: "var(--ink-faint)" }}>
            No trending stories here right now — check back soon.
          </p>
        ) : (
          stories.map((s, i) => <StoryRow key={s.slug} story={s} rank={i + 1} />)
        )}
      </div>
      </div>

      <ScopeSheet
        open={scopeOpen}
        onClose={() => setScopeOpen(false)}
        options={scopeOpts}
        selected={scope}
        onSelect={chooseScope}
        disabledReason={(v) => (v === "region" && !state ? "Add your state in Your Prism to filter by region" : null)}
      />
    </div>
  );
}

function StoryRow({ story, rank }: { story: TrendingStory; rank: number }) {
  return (
    <Link href={`/trending/${story.slug}`} className="flex items-start gap-3 border-b px-5 py-[13px]" style={{ borderColor: "var(--line)" }}>
      <span
        className="w-[26px] shrink-0 text-[24px] font-semibold leading-none"
        style={{ fontFamily: "var(--font-display), serif", color: rank === 1 ? "var(--ink)" : "var(--ink-faint)" }}
      >
        {rank}
      </span>
      <div className="min-w-0 flex-1">
        {/* The storyline's NAME, not one outlet's headline. `label` is the cast
            we generated for the cluster — "Delhi Police · Sonam Wangchuk · Narendra
            Modi" — which is what the story page shows and what makes a row read as
            a running story rather than a single article. hero_title is one
            member's headline and was winning here, so the list and the page it
            opened disagreed about what the story was called. */}
        <p className="text-[15.5px] font-semibold leading-[1.35]">{story.label ?? story.hero_title}</p>
        <p className="mt-1 font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
          {story.source_count} outlets ·{" "}
          {story.velocity > 0 ? <span style={{ color: "var(--up)" }}>developing</span> : `${story.developments} updates`}
        </p>
      </div>
      <span className="relative block h-14 w-14 shrink-0 overflow-hidden rounded-xl border" style={{ background: "var(--bg-sunken)", borderColor: "var(--line)" }}>
        {story.hero_image && (
          <Image
            src={thumbUrl(story.hero_image, THUMB_W)}
            alt=""
            fill
            sizes="56px"
            className="object-cover"
            onError={(e) => {
              (e.currentTarget.parentElement as HTMLElement).style.display = "none";
            }}
          />
        )}
      </span>
    </Link>
  );
}

function SkeletonRow() {
  return (
    <div className="flex items-start gap-3 border-b px-5 py-[13px]" style={{ borderColor: "var(--line)" }}>
      <span className="w-[26px] shrink-0" />
      <div className="min-w-0 flex-1 space-y-2 pt-1">
        <span className="block h-[14px] w-3/4 animate-pulse rounded" style={{ background: "var(--bg-sunken)" }} />
        <span className="block h-[10px] w-2/5 animate-pulse rounded" style={{ background: "var(--bg-sunken)" }} />
      </div>
      <span className="block h-14 w-14 shrink-0 animate-pulse rounded-xl" style={{ background: "var(--bg-sunken)" }} />
    </div>
  );
}

