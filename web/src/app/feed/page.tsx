"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { ParseMark } from "@/components/ParseMark";
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
import { useScrollRestore } from "@/lib/useScrollRestore";
import { useSession } from "@/lib/session";
import { watchlistEvents, type WatchEvent } from "@/lib/watchlist";

type Scope = "all" | "region" | "world";

// Session-scoped cache so returning from a story restores the feed instantly at
// the reader's scroll position (no reload/skeleton, no scroll-to-top). Lives at
// module scope: survives client navigations, cleared on a full page reload.
type FeedCache = {
  items: FeedItem[] | null;
  top: FeedItem[];
  digest: MarketDigest | null;
  trending: TrendingStory[];
  scope: Scope;
};
let feedCache: FeedCache | null = null;

// Sector → lens hue for the tiny section marker dot (color only ever means a lens).
function sectorLens(slug: string): string | null {
  if (/(market|financ|business|econom)/i.test(slug)) return "var(--lens-finance)";
  if (/(cyber|security)/i.test(slug)) return "var(--lens-cyber)";
  return null;
}

export default function FeedPage() {
  const taxonomy = useTaxonomy();
  const session = useSession();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [lens, setLens] = useState("reader");
  const [scope, setScope] = useState<Scope>(() => feedCache?.scope ?? "all");
  const [scopeOpen, setScopeOpen] = useState(false);
  const [stateName, setStateName] = useState<string | null>(null);
  const [items, setItems] = useState<FeedItem[] | null>(() => feedCache?.items ?? null);
  const [top, setTop] = useState<FeedItem[]>(() => feedCache?.top ?? []);
  const [error, setError] = useState<string | null>(null);
  const [digest, setDigest] = useState<MarketDigest | null>(() => feedCache?.digest ?? null);
  const [trending, setTrending] = useState<TrendingStory[]>(() => feedCache?.trending ?? []);
  const [watch, setWatch] = useState<WatchEvent[]>([]);
  const restoredCache = useRef(feedCache !== null);

  useEffect(() => {
    const p = loadProfile();
    setProfile(p);
    if (p?.lens) setLens(p.lens);
    if (p?.state && !restoredCache.current) setScope("region"); // default to the reader's state (unless restored)
  }, []);

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
    fetchTrending({ state: profile?.state, limit: 4 }).then(setTrending).catch(() => setTrending([]));
  }, [profile?.state]);

  useEffect(() => {
    if (!session) {
      setWatch([]);
      return;
    }
    watchlistEvents(session).then(setWatch).catch(() => setWatch([]));
  }, [session]);

  useEffect(() => {
    // Keep showing cached/previous items while re-fetching (stale-while-revalidate)
    // so returning from a story doesn't flash a skeleton or lose the reader's place.
    setError(null);
    const query = {
      lens,
      interests: lens === "reader" ? profile?.interests : undefined,
      region: profile?.region,
      state: profile?.state,
      languages: profile?.languages,
    };
    // Profile loads after the first render, so two fetches are in flight on mount.
    // Without this flag a slow un-personalized response can land last and overwrite
    // the personalized one — national stories under a "Your state" chip.
    let cancelled = false;
    Promise.all([fetchFeed({ ...query, sort: "latest" }), fetchFeed({ ...query, sort: "top" })])
      .then(([list, ranked]) => {
        if (cancelled) return;
        setItems(list);
        setTop(ranked.slice(0, 3));
      })
      .catch(() => {
        if (!cancelled) setError("The Parse API is unreachable right now. Refresh in a moment.");
      });
    return () => {
      cancelled = true;
    };
  }, [lens, profile]);

  // Mirror the feed DATA into the module cache so a return navigation renders
  // instantly (no skeleton). Scroll lives in sessionStorage (survives everything).
  useEffect(() => {
    // Only cache once there's actually a feed. Writing on the first mount
    // installs a non-null-but-empty cache, which makes every later mount think
    // it restored — silently losing the reader's state-default scope for the
    // rest of the session.
    if (items === null) return;
    feedCache = { items, top, digest, trending, scope };
  }, [items, top, digest, trending, scope]);

  // Restore scroll on return from a story (data comes from the module cache above).
  useScrollRestore("feed:scrollY", items !== null);

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

  const nameOf = (slug: string) => taxonomy.find((s) => s.slug === slug)?.name ?? slug.replaceAll("_", " ");

  const sections = useMemo(() => {
    const bySector = new Map<string, FeedItem[]>();
    for (const item of sectionItems) {
      const key = item.sector ?? "other";
      bySector.set(key, [...(bySector.get(key) ?? []), item]);
    }
    return [...bySector.entries()].map(([slug, list]) => ({ slug, title: nameOf(slug), items: list }));
  }, [sectionItems, taxonomy]);

  const sectorCount = useMemo(() => {
    const m = new Map<string, number>();
    for (const i of visible ?? []) {
      const k = i.sector ?? "other";
      m.set(k, (m.get(k) ?? 0) + 1);
    }
    return m;
  }, [visible]);

  const lead = visibleTop[0] ?? null;
  const pulse = lensMeta("markets");
  const languages = profile?.languages?.length ? profile.languages : ["en"];
  const primaryLang = languages[0];
  const scopeLabel = scope === "region" ? stateName ?? "Your state" : scope === "world" ? "National" : "World";

  const scopeOpts: [Scope, string][] = [
    ["region", stateName ? `Your state — ${stateName}` : "Your state"],
    ["world", "National"],
    ["all", "World"],
  ];

  return (
    <div className="relative mx-auto min-w-0 max-w-[620px] pb-28">
      {/* header: scope chip + language */}
      <div
        className="sticky top-0 z-20 flex items-center gap-2.5 border-b px-5 py-2.5 backdrop-blur-md"
        style={{ borderColor: "var(--line)", background: "var(--glass)" }}
      >
        <Link href="/" className="flex items-center gap-2" style={{ color: "var(--ink)" }}>
          <ParseMark />
          <span className="text-[19px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
            Parse
          </span>
        </Link>
        <button
          onClick={() => setScopeOpen(true)}
          className="ml-auto inline-flex h-9 items-center gap-1.5 rounded-full border px-3.5 text-[12.5px] font-semibold"
          style={{ borderColor: "var(--line-strong)", background: "var(--bg-elevated)", color: "var(--ink)" }}
        >
          ◉ {scopeLabel} <span style={{ color: "var(--ink-faint)" }}>▾</span>
        </button>
        <Link
          href="/interests"
          title="Language preferences — rank the feed, never filter it"
          className="flex h-9 items-center gap-1.5 rounded-full border px-3 text-[11px] font-semibold"
          style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
        >
          <svg aria-hidden width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <circle cx="12" cy="12" r="9" />
            <path d="M3 12h18M12 3c2.5 2.6 3.8 5.7 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.7-3.8-9s1.3-6.4 3.8-9Z" />
          </svg>
          {languages.slice(0, 2).map(langNative).join(" · ")}
        </Link>
      </div>

      {error && (
        <div className="mx-5 mt-4 rounded-[18px] border p-5 text-sm" style={{ borderColor: "var(--danger)", background: "var(--danger-bg)", color: "var(--danger)" }}>
          {error}
        </div>
      )}

      {!error && visible === null && (
        <div className="space-y-3 px-5 pt-4">
          <div className="h-[210px] animate-pulse rounded-[18px]" style={{ background: "var(--bg-sunken)" }} />
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-[18px]" style={{ background: "var(--bg-sunken)" }} />
          ))}
        </div>
      )}

      {!error && visible !== null && visible.length === 0 && (
        <div className="mx-5 mt-4 rounded-[18px] border p-[26px] text-sm" style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}>
          No stories here yet — widen your interests or check back shortly.
        </div>
      )}

      {/* lead story */}
      {!error && lead && (
        <div className="stagger px-5 pt-3.5" key={`top-${lens}-${scope}`}>
          <TopStoryCard item={lead} lens={lens} primaryLang={primaryLang} />
        </div>
      )}

      {/* what's moving */}
      {trending.length > 0 && (
        <>
          <div className="flex items-baseline justify-between px-5 pb-1.5 pt-4">
            <h2 className="text-[12px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-muted)" }}>
              What&rsquo;s moving
            </h2>
            <Link href="/trending" className="text-[12px] font-semibold" style={{ color: "var(--ink-faint)" }}>
              Trending →
            </Link>
          </div>
          <div className="hide-scroll flex gap-2.5 overflow-x-auto px-5 pb-1.5">
            {trending.slice(0, 4).map((t, i) => (
              <Link
                key={t.slug}
                href={`/trending/${t.slug}`}
                className="flex w-[226px] flex-none items-start gap-2.5 rounded-[14px] border p-3"
                style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
              >
                <span className="text-[19px] font-semibold leading-none" style={{ fontFamily: "var(--font-display), serif", color: "var(--ink-faint)" }}>
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[12.5px] font-semibold leading-[1.35]">{t.hero_title ?? t.label}</p>
                  <span className="mt-1 block font-mono text-[10px]" style={{ color: "var(--ink-faint)" }}>
                    {t.source_count} sources · {t.velocity >= 3 ? "developing" : `${t.developments} updates`}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </>
      )}

      {/* sticky sector chips */}
      {sections.length > 0 && (
        <div
          className="hide-scroll sticky top-[53px] z-10 mt-3 flex gap-2 overflow-x-auto border-y px-5 py-2.5 backdrop-blur-md"
          style={{ borderColor: "var(--line)", background: "var(--glass)" }}
        >
          <a href="#for-you" className="flex-none whitespace-nowrap rounded-full px-3.5 py-1.5 text-[12px] font-semibold" style={{ background: "var(--ink)", color: "var(--bg)" }}>
            For you
          </a>
          {sections.map((sec) => (
            <a
              key={sec.slug}
              href={`#sector-${sec.slug}`}
              className="flex-none whitespace-nowrap rounded-full border px-3.5 py-1.5 text-[12px] font-semibold"
              style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
            >
              {sec.title}
            </a>
          ))}
        </div>
      )}

      {/* sections + inline pulse */}
      {!error &&
        sections.map((sec, idx) => {
          const dot = sectorLens(sec.slug);
          return (
            <div key={sec.slug}>
              <section id={`sector-${sec.slug}`} className="scroll-mt-28 pt-2">
                <div className="flex items-baseline justify-between px-5 pb-1 pt-3">
                  <h2 className="flex items-center gap-2 text-[12px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-muted)" }}>
                    {dot && <span className="h-[7px] w-[7px] rounded-full" style={{ background: dot }} />}
                    {sec.title}
                  </h2>
                  <Link href={`/sector/${sec.slug}`} className="text-[12px] font-semibold" style={{ color: "var(--ink-faint)" }}>
                    All {sectorCount.get(sec.slug) ?? sec.items.length} →
                  </Link>
                </div>
                <div className="flex flex-col">
                  {sec.items.map((item) => (
                    <StoryRowCard key={item.id} item={item} lens={lens} primaryLang={primaryLang} />
                  ))}
                </div>
              </section>

              {/* inline market pulse after the first section */}
              {idx === 0 && digest && (
                <Link
                  href="/pulse"
                  className="card-hover mx-5 mt-4 block rounded-[16px] border p-4"
                  style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
                >
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-muted)" }}>
                      <span className="h-[7px] w-[7px] rounded-full" style={{ background: pulse.color }} />
                      Market pulse
                    </span>
                    <span className="text-[12px] font-semibold" style={{ color: "var(--ink-faint)" }}>
                      Open →
                    </span>
                  </div>
                  <p className="mt-2 text-[14px] font-semibold leading-[1.4]" style={{ color: "var(--ink)" }}>
                    {digest.headline}
                  </p>
                  <p className="mt-1.5 font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
                    {digest.generated_at ? `Updated ${timeAgo(digest.generated_at)} · ` : ""}
                    {digest.event_ids.length} stories
                  </p>
                </Link>
              )}
            </div>
          );
        })}

      {/* following strip */}
      {session && watch.length > 0 && (
        <section className="pt-2">
          <div className="flex items-baseline justify-between px-5 pb-1 pt-4">
            <h2 className="text-[12px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-muted)" }}>
              Following
            </h2>
            <Link href="/you" className="text-[12px] font-semibold" style={{ color: "var(--ink-faint)" }}>
              You →
            </Link>
          </div>
          <div className="flex flex-col">
            {watch.slice(0, 4).map((w) => (
              <Link key={w.id} href={`/story/${w.id}`} className="border-b px-5 py-3" style={{ borderColor: "var(--line)" }}>
                <p className="text-[14px] font-semibold leading-[1.4]" style={{ color: "var(--ink)" }}>
                  {w.title}
                </p>
                <span className="mt-1 block font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
                  followed · {timeAgo(w.last_updated_at)}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* scope bottom sheet */}
      {scopeOpen && (
        <div className="fixed inset-0 z-50 flex flex-col justify-end lg:absolute">
          <button aria-label="Close" onClick={() => setScopeOpen(false)} className="absolute inset-0" style={{ background: "rgba(15,14,12,.4)" }} />
          <div className="relative rounded-t-[22px] px-5 pb-11 pt-3" style={{ background: "var(--bg-elevated)", boxShadow: "var(--shadow-pop)" }}>
            <div className="mx-auto mb-3.5 h-1 w-9 rounded-full" style={{ background: "var(--line-strong)" }} />
            <h3 className="text-[18px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
              Scope
            </h3>
            <p className="mb-3 mt-1 text-[12.5px]" style={{ color: "var(--ink-muted)" }}>
              Applies everywhere — Feed, Trending, Pulse and Search.
            </p>
            {scopeOpts.map(([value, label]) => (
              <button
                key={value}
                onClick={() => {
                  setScope(value);
                  setScopeOpen(false);
                }}
                disabled={value !== "all" && !profile?.state}
                className="flex min-h-[48px] w-full items-center gap-2.5 border-b px-1 text-left text-[14.5px] disabled:opacity-40"
                style={{ borderColor: "var(--line)", color: "var(--ink)", fontWeight: scope === value ? 600 : 500 }}
              >
                <span>{label}</span>
                {scope === value && <span className="ml-auto">✓</span>}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
