"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { StoryRowCard, TopStoryCard, timeAgo } from "@/components/StoryCard";
import { useTaxonomy } from "@/components/ProfileEditor";
import { fetchDigest, fetchFeed, type FeedItem, type MarketDigest } from "@/lib/api";
import { lensMeta, useLenses } from "@/lib/lenses";
import { loadProfile, saveProfile, type Profile } from "@/lib/profile";
import { useSession } from "@/lib/session";
import { watchlistEvents, type WatchEvent } from "@/lib/watchlist";

function Pill({
  selected,
  color,
  bg,
  onClick,
  children,
}: {
  selected: boolean;
  color?: string;
  bg?: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      role="tab"
      aria-selected={selected}
      onClick={onClick}
      className="whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-semibold transition"
      style={
        selected
          ? color
            ? { background: bg, color, boxShadow: `inset 0 0 0 1.5px ${color}` }
            : { background: "var(--ink)", color: "var(--bg)" }
          : { color: "var(--ink-muted)" }
      }
    >
      {children}
    </button>
  );
}

type Scope = "all" | "region" | "world";

export default function FeedPage() {
  const taxonomy = useTaxonomy();
  const lenses = useLenses();
  const session = useSession();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [lens, setLens] = useState("reader");
  const [sort, setSort] = useState<"latest" | "top">("latest");
  const [scope, setScope] = useState<Scope>("all");
  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [top, setTop] = useState<FeedItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [digest, setDigest] = useState<MarketDigest | null>(null);
  const [watch, setWatch] = useState<WatchEvent[]>([]);

  useEffect(() => {
    const p = loadProfile();
    setProfile(p);
    if (p?.lens) setLens(p.lens);
  }, []);

  useEffect(() => {
    fetchDigest().then(setDigest).catch(() => setDigest(null));
  }, []);

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
      fetchFeed({ ...query, sort }),
      // The "Top stories" block is always score-ranked, whatever the list sort.
      fetchFeed({ ...query, sort: "top" }),
    ])
      .then(([list, ranked]) => {
        setItems(list);
        setTop(ranked.slice(0, 3));
      })
      .catch(() => setError("The Prism API is unreachable right now. Refresh in a moment."));
  }, [lens, sort, profile]);

  function switchLens(slug: string) {
    setLens(slug);
    if (profile) saveProfile({ ...profile, lens: slug });
    else saveProfile({ lens: slug, region: null, state: null, interests: [] });
  }

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

  // Full per-sector counts (includes the stories pulled into the lead block) for
  // the rail and the "All N →" headers.
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

  const blindspots = useMemo(
    () => (visible ?? []).filter((i) => i.coverage?.single_origin).slice(0, 2),
    [visible],
  );

  const meta = lensMeta(lens);
  const pulse = lensMeta("markets");

  const railItem =
    "flex items-center justify-between rounded-[10px] px-3 py-2 text-[13.5px] transition";

  return (
    <div className="mx-auto max-w-[1320px] px-5 pb-24 pt-5 sm:px-8 lg:grid lg:grid-cols-[200px_1fr_300px] lg:items-start lg:gap-8 lg:pb-20 lg:pt-6 xl:px-10">
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
      <aside className="hidden flex-col gap-0.5 lg:sticky lg:top-20 lg:flex">
        <span
          className="px-3 pb-2 text-[10.5px] font-semibold uppercase tracking-[0.14em]"
          style={{ color: "var(--ink-faint)" }}
        >
          Sections
        </span>
        <a href="#for-you" className={`${railItem} font-semibold`} style={{ background: "var(--bg-sunken)", color: "var(--ink)" }}>
          For you
        </a>
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
          <div className="max-w-full overflow-x-auto">
            <div className="flex w-max gap-1 rounded-full border p-1" style={{ borderColor: "var(--line)" }} role="tablist" aria-label="Lens">
              {lenses.map((m) => (
                <Pill key={m.slug} selected={lens === m.slug} color={m.color} bg={m.bg} onClick={() => switchLens(m.slug)}>
                  {m.short}
                </Pill>
              ))}
              <span
                title="More lenses are on the way"
                className="rounded-full border border-dashed px-3 py-1.5 text-xs font-semibold"
                style={{ borderColor: "var(--line-strong)", color: "var(--ink-faint)" }}
              >
                +
              </span>
            </div>
          </div>
        </div>

        <div className="mb-5 flex flex-wrap items-center gap-2">
          <p className="text-[13px]" style={{ color: "var(--ink-muted)" }}>
            {meta.tagline}.
          </p>
          {profile?.state && (
            <div className="flex gap-0.5 rounded-full border p-1" style={{ borderColor: "var(--line)" }} role="tablist" aria-label="Scope">
              {(
                [
                  ["all", "All"],
                  ["region", "My state"],
                  ["world", "National"],
                ] as [Scope, string][]
              ).map(([value, label]) => (
                <Pill key={value} selected={scope === value} onClick={() => setScope(value)}>
                  {label}
                </Pill>
              ))}
            </div>
          )}
          <div className="ml-auto flex gap-0.5 rounded-full border p-1" style={{ borderColor: "var(--line)" }} role="tablist" aria-label="Sort">
            {(
              [
                ["latest", "Latest"],
                ["top", "Top"],
              ] as ["latest" | "top", string][]
            ).map(([value, label]) => (
              <Pill key={value} selected={sort === value} onClick={() => setSort(value)}>
                {label}
              </Pill>
            ))}
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
            <TopStoryCard item={lead} lens={lens} />
            {secondary.length > 0 && (
              <div className="mt-3.5 grid gap-3.5 sm:grid-cols-2">
                {secondary.map((item) => (
                  <TopStoryCard key={item.id} item={item} lens={lens} />
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
                  <StoryRowCard key={item.id} item={item} lens={lens} />
                ))}
              </div>
            </section>
          ))}
      </div>

      {/* Right context rail */}
      <aside className="hidden flex-col gap-3.5 lg:sticky lg:top-20 lg:flex">
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

        {blindspots.length > 0 && (
          <div className="rounded-[18px] border p-5" style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}>
            <span className="text-[10.5px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
              Blindspot watch
            </span>
            <div className="mt-2.5 flex flex-col gap-3">
              {blindspots.map((i) => (
                <Link key={i.id} href={`/story/${i.id}`} className="block">
                  <p className="text-[13px] font-semibold leading-[1.45]" style={{ color: "var(--ink)" }}>
                    {i.title}
                  </p>
                  <p className="mt-1 text-[11.5px] leading-[1.45]" style={{ color: "var(--ink-faint)" }}>
                    ⚠ Single-origin — {i.source_count} source{i.source_count === 1 ? "" : "s"}, one country so far.
                  </p>
                </Link>
              ))}
            </div>
          </div>
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
