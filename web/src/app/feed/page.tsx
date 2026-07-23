"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { StoryRowCard, TopStoryCard, timeAgo } from "@/components/StoryCard";
import { useTaxonomy } from "@/components/ProfileEditor";
import {
  fetchDigest,
  fetchFeed,
  fetchRegions,
  fetchTrending,
  type FeedItem,
  type MarketDigest,
  type TrendingStory,
} from "@/lib/api";
import { langNative } from "@/lib/languages";
import { lensMeta } from "@/lib/lenses";
import { loadProfile, type Profile } from "@/lib/profile";
import { useSession } from "@/lib/session";
import { watchlistEvents, type WatchEvent } from "@/lib/watchlist";

function Pill({
  selected,
  onClick,
  children,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      role="tab"
      aria-selected={selected}
      onClick={onClick}
      className="whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-semibold transition"
      style={selected ? { background: "var(--ink)", color: "var(--bg)" } : { color: "var(--ink-muted)" }}
    >
      {children}
    </button>
  );
}

type Scope = "all" | "region" | "world";

export default function FeedPage() {
  const taxonomy = useTaxonomy();
  const session = useSession();
  const [profile, setProfile] = useState<Profile | null>(null);
  // Lens is read from the saved profile only. The feed no longer filters by lens,
  // and there's no lens switcher in the chrome — the lens is set in "Your Prism"
  // (/interests) and flipped per-story in the story view.
  const [lens, setLens] = useState("reader");
  const [scope, setScope] = useState<Scope>("all");
  const [stateName, setStateName] = useState<string | null>(null);
  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [top, setTop] = useState<FeedItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [digest, setDigest] = useState<MarketDigest | null>(null);
  const [trending, setTrending] = useState<TrendingStory[]>([]);
  const [watch, setWatch] = useState<WatchEvent[]>([]);

  useEffect(() => {
    const p = loadProfile();
    setProfile(p);
    if (p?.lens) setLens(p.lens);
  }, []);

  // Resolve the reader's state code (IN-KA) to its display name (Karnataka) for
  // the scope tab; falls back to "My state" if the regions list is unavailable.
  useEffect(() => {
    if (!profile?.state) return;
    fetchRegions()
      .then((rs) => setStateName(rs.find((r) => r.code === profile.state)?.name ?? null))
      .catch(() => setStateName(null));
  }, [profile?.state]);

  useEffect(() => {
    fetchDigest().then(setDigest).catch(() => setDigest(null));
  }, []);

  useEffect(() => {
    fetchTrending({ state: profile?.state, limit: 3 }).then(setTrending).catch(() => setTrending([]));
  }, [profile?.state]);

  useEffect(() => {
    if (!session) {
      setWatch([]);
      return;
    }
    watchlistEvents(session).then(setWatch).catch(() => setWatch([]));
  }, [session]);

  useEffect(() => {
    setItems(null);
    setError(null);
    const query = {
      lens,
      interests: lens === "reader" ? profile?.interests : undefined,
      region: profile?.region,
      state: profile?.state,
      languages: profile?.languages,
    };
    Promise.all([
      fetchFeed({ ...query, sort: "latest" }),
      // The lead block is always score-ranked, whatever the list order.
      fetchFeed({ ...query, sort: "top" }),
    ])
      .then(([list, ranked]) => {
        setItems(list);
        setTop(ranked.slice(0, 3));
      })
      .catch(() => setError("The Prism API is unreachable right now. Refresh in a moment."));
  }, [lens, profile]);

  const visible = useMemo(() => {
    if (!items || scope === "all" || !profile?.state) return items;
    return items.filter((i) => (scope === "region" ? i.is_regional : !i.is_regional));
  }, [items, scope, profile]);

  const topIds = useMemo(() => new Set(top.map((t) => t.id)), [top]);
  const sectionItems = useMemo(() => (visible ?? []).filter((i) => !topIds.has(i.id)), [visible, topIds]);
  const visibleTop = useMemo(() => {
    if (scope === "all" || !profile?.state) return top;
    return top.filter((i) => (scope === "region" ? i.is_regional : !i.is_regional));
  }, [top, scope, profile]);

  const nameOf = (slug: string) =>
    taxonomy.find((s) => s.slug === slug)?.name ?? slug.replaceAll("_", " ");

  const sections = useMemo(() => {
    const bySector = new Map<string, FeedItem[]>();
    for (const item of sectionItems) {
      const key = item.sector ?? "other";
      bySector.set(key, [...(bySector.get(key) ?? []), item]);
    }
    return [...bySector.entries()].map(([slug, list]) => ({ slug, title: nameOf(slug), items: list }));
  }, [sectionItems, taxonomy]);

  // Full per-sector counts (includes stories pulled into the lead block).
  const sectorCount = useMemo(() => {
    const m = new Map<string, number>();
    for (const i of visible ?? []) {
      const k = i.sector ?? "other";
      m.set(k, (m.get(k) ?? 0) + 1);
    }
    return m;
  }, [visible]);

  const lead = visibleTop[0] ?? null;
  const secondary = visibleTop.slice(1, 3);

  const pulse = lensMeta("markets");
  const languages = profile?.languages?.length ? profile.languages : ["en"];
  const primaryLang = languages[0];
  const languageLabel = languages.slice(0, 3).map(langNative).join(" · ");

  const railItem =
    "flex items-center justify-between rounded-[10px] px-3 py-2 text-[13.5px] transition";

  return (
    <div className="mx-auto max-w-[1240px] px-5 pb-24 pt-6 sm:px-8 lg:grid lg:grid-cols-[200px_1fr_300px] lg:items-start lg:gap-8 lg:pb-20 xl:px-10">
      {/* Mobile sector chip rail */}
      <div
        className="sticky top-[52px] z-30 -mx-5 mb-3 flex gap-1.5 overflow-x-auto border-b px-5 py-2.5 sm:-mx-8 sm:px-8 lg:hidden"
        style={{ borderColor: "var(--line)", background: "var(--glass)" }}
      >
        <a
          href="#for-you"
          className="flex-none whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-semibold"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          For you
        </a>
        {sections.map((sec) => (
          <a
            key={sec.slug}
            href={`#sector-${sec.slug}`}
            className="flex-none whitespace-nowrap rounded-full border px-3.5 py-1.5 text-xs font-semibold"
            style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
          >
            {sec.title}
          </a>
        ))}
      </div>

      {/* Left sector rail */}
      <aside className="hidden flex-col gap-0.5 lg:sticky lg:top-[72px] lg:flex">
        <span
          className="px-3 pb-2 text-[10.5px] font-semibold uppercase tracking-[0.14em]"
          style={{ color: "var(--ink-faint)" }}
        >
          Sections
        </span>
        <a href="#for-you" className={`${railItem} font-semibold`} style={{ background: "var(--bg-sunken)", color: "var(--ink)" }}>
          For you
        </a>
        <Link href="/trending" className={`${railItem} font-medium`} style={{ color: "var(--ink-muted)" }}>
          Trending
        </Link>
        {sections.length > 0 && <span className="mx-3 my-2 h-px" style={{ background: "var(--line)" }} />}
        {sections.map((sec) => (
          <Link
            key={sec.slug}
            href={`/sector/${sec.slug}`}
            className={`${railItem} font-medium`}
            style={{ color: "var(--ink-muted)" }}
          >
            {sec.title}
            <span className="font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
              {sectorCount.get(sec.slug) ?? sec.items.length}
            </span>
          </Link>
        ))}
        <span className="mx-3 my-2 h-px" style={{ background: "var(--line)" }} />
        <Link href="/interests" className={`${railItem} text-[12.5px] font-medium`} style={{ color: "var(--ink-faint)" }}>
          Edit interests
        </Link>
      </aside>

      {/* Main column */}
      <div className="min-w-0">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3" id="for-you">
          <h1 className="text-[26px] font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            For you
          </h1>
          <div className="flex flex-wrap items-center gap-2">
            {profile?.state && (
              <div className="flex gap-0.5 rounded-full border p-1" style={{ borderColor: "var(--line)" }} role="tablist" aria-label="Scope">
                {(
                  [
                    ["all", "All"],
                    ["region", stateName ?? "My state"],
                    ["world", "National"],
                  ] as [Scope, string][]
                ).map(([value, label]) => (
                  <Pill key={value} selected={scope === value} onClick={() => setScope(value)}>
                    {label}
                  </Pill>
                ))}
              </div>
            )}
            <Link
              href="/interests"
              title="Language preferences — rank the feed, never filter it"
              className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold"
              style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
            >
              <svg aria-hidden width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="12" cy="12" r="9" />
                <path d="M3 12h18M12 3c2.5 2.6 3.8 5.7 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.7-3.8-9s1.3-6.4 3.8-9Z" />
              </svg>
              {languageLabel}
            </Link>
          </div>
        </div>

        {error && (
          <div className="rounded-[18px] border p-5 text-sm" style={{ borderColor: "var(--danger)", background: "var(--danger-bg)", color: "var(--danger)" }}>
            {error}
          </div>
        )}

        {!error && visible === null && (
          <div className="space-y-3">
            <div className="h-[220px] animate-pulse rounded-[18px]" style={{ background: "var(--bg-sunken)" }} />
            <div className="grid gap-3.5 sm:grid-cols-2">
              {[...Array(2)].map((_, i) => (
                <div key={i} className="h-28 animate-pulse rounded-[18px]" style={{ background: "var(--bg-sunken)" }} />
              ))}
            </div>
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-24 animate-pulse rounded-[18px]" style={{ background: "var(--bg-sunken)" }} />
            ))}
          </div>
        )}

        {!error && visible !== null && visible.length === 0 && (
          <div className="rounded-[18px] border p-[26px] text-sm" style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}>
            No stories here yet — widen your interests or check back shortly.
          </div>
        )}

        {!error && visible !== null && lead && (
          <div className="stagger" key={`top-${lens}-${scope}`}>
            <TopStoryCard item={lead} lens={lens} primaryLang={primaryLang} />
            {secondary.length > 0 && (
              <div className="mt-3.5 grid gap-3.5 sm:grid-cols-2">
                {secondary.map((item) => (
                  <TopStoryCard key={item.id} item={item} lens={lens} primaryLang={primaryLang} />
                ))}
              </div>
            )}
          </div>
        )}

        {!error &&
          sections.map((sec) => (
            <section key={sec.slug} id={`sector-${sec.slug}`} className="mt-7 scroll-mt-24">
              <div className="mb-3 flex items-baseline gap-3">
                <Link
                  href={`/sector/${sec.slug}`}
                  className="text-[18px] font-semibold"
                  style={{ fontFamily: "var(--font-display), serif", color: "var(--ink)" }}
                >
                  {sec.title}
                </Link>
                <span className="h-px flex-1" style={{ background: "var(--line)" }} />
                <Link href={`/sector/${sec.slug}`} className="text-xs font-semibold" style={{ color: "var(--ink-faint)" }}>
                  All {sectorCount.get(sec.slug) ?? sec.items.length} →
                </Link>
              </div>
              <div className="flex flex-col gap-2.5">
                {sec.items.map((item) => (
                  <StoryRowCard key={item.id} item={item} lens={lens} primaryLang={primaryLang} />
                ))}
              </div>
            </section>
          ))}
      </div>

      {/* Right context rail */}
      <aside className="hidden flex-col gap-3.5 lg:sticky lg:top-[72px] lg:flex">
        {trending.length > 0 && (
          <div className="rounded-[18px] border p-5" style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}>
            <span className="text-[10.5px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
              Trending now
            </span>
            <div className="mt-2.5 flex flex-col gap-2.5">
              {trending.slice(0, 3).map((t, i) => (
                <Link key={t.slug} href={`/trending/${t.slug}`} className="flex items-baseline gap-2.5">
                  <span className="shrink-0 font-mono text-[12px]" style={{ color: "var(--ink-faint)" }}>
                    {i + 1}
                  </span>
                  <span className="text-[13px] font-semibold leading-[1.4]" style={{ color: "var(--ink)" }}>
                    {t.hero_title ?? t.label}
                    {t.velocity >= 3 && (
                      <span
                        className="ml-1.5 whitespace-nowrap rounded-full px-[7px] py-px text-[9.5px] font-semibold"
                        style={{ background: "var(--up-bg)", color: "var(--up)" }}
                      >
                        developing
                      </span>
                    )}
                  </span>
                </Link>
              ))}
            </div>
            <Link href="/trending" className="mt-2.5 block text-[12px] font-semibold" style={{ color: "var(--ink)" }}>
              All trending →
            </Link>
          </div>
        )}

        {digest && (
          <Link
            href="/pulse"
            className="card-hover block rounded-[18px] border p-5"
            style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
          >
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ background: pulse.color }} />
              <span className="text-[10.5px] font-semibold uppercase tracking-[0.14em]" style={{ color: pulse.color }}>
                Market Pulse
              </span>
            </span>
            <p className="mt-2.5 text-[15.5px] font-semibold leading-[1.35]" style={{ fontFamily: "var(--font-display), serif", color: "var(--ink)" }}>
              {digest.headline}
            </p>
            <p className="mt-1.5 font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
              {digest.generated_at ? `Updated ${timeAgo(digest.generated_at)} · ` : ""}
              {digest.event_ids.length} stories
            </p>
            <p className="mt-2.5 text-[12.5px] font-semibold" style={{ color: "var(--ink)" }}>
              Read today&rsquo;s pulse →
            </p>
          </Link>
        )}

        <div className="rounded-[18px] border p-5" style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}>
          <span className="text-[10.5px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
            Following
          </span>
          {session ? (
            watch.length > 0 ? (
              <div className="mt-2.5 flex flex-col gap-2">
                {watch.slice(0, 5).map((w) => (
                  <Link key={w.id} href={`/story/${w.id}`} className="flex items-baseline justify-between gap-3">
                    <span className="line-clamp-1 text-[13px] font-medium" style={{ color: "var(--ink)" }}>
                      {w.title}
                    </span>
                    <span className="shrink-0 font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
                      {timeAgo(w.last_updated_at)}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="mt-2.5 text-[12.5px]" style={{ color: "var(--ink-faint)" }}>
                Nothing followed yet. Follow tickers and sectors from any story.
              </p>
            )
          ) : (
            <Link href="/signin" className="mt-2.5 block text-[12.5px] font-semibold" style={{ color: "var(--ink)" }}>
              Sign in to follow stories →
            </Link>
          )}
        </div>
      </aside>
    </div>
  );
}
