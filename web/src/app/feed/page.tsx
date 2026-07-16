"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { StoryRowCard, TopStoryCard } from "@/components/StoryCard";
import { useTaxonomy } from "@/components/ProfileEditor";
import { fetchFeed, type FeedItem } from "@/lib/api";
import { LENS_ORDER, lensMeta } from "@/lib/lenses";
import { loadProfile, saveProfile, type Profile } from "@/lib/profile";

function regionName(code: string): string {
  try {
    return new Intl.DisplayNames(["en"], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}

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
  const [profile, setProfile] = useState<Profile | null>(null);
  const [lens, setLens] = useState("general");
  const [sort, setSort] = useState<"latest" | "top">("latest");
  const [scope, setScope] = useState<Scope>("all");
  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [top, setTop] = useState<FeedItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const p = loadProfile();
    setProfile(p);
    if (p?.lens) setLens(p.lens);
  }, []);

  useEffect(() => {
    setItems(null);
    setError(null);
    const query = {
      lens,
      interests: lens === "general" ? profile?.interests : undefined,
      region: profile?.region,
    };
    Promise.all([
      fetchFeed({ ...query, sort }),
      // The "Top stories" rail is always score-ranked, whatever the list sort.
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
    else saveProfile({ lens: slug, region: null, interests: [] });
  }

  const visible = useMemo(() => {
    if (!items || scope === "all" || !profile?.region) return items;
    return items.filter((i) => (scope === "region" ? i.is_regional : !i.is_regional));
  }, [items, scope, profile]);

  const topIds = useMemo(() => new Set(top.map((t) => t.id)), [top]);
  const sectionItems = useMemo(() => (visible ?? []).filter((i) => !topIds.has(i.id)), [visible, topIds]);
  const visibleTop = useMemo(() => {
    if (scope === "all" || !profile?.region) return top;
    return top.filter((i) => (scope === "region" ? i.is_regional : !i.is_regional));
  }, [top, scope, profile]);

  const sections = useMemo(() => {
    const bySector = new Map<string, FeedItem[]>();
    for (const item of sectionItems) {
      const key = item.sector ?? "other";
      bySector.set(key, [...(bySector.get(key) ?? []), item]);
    }
    const nameOf = (slug: string) => taxonomy.find((s) => s.slug === slug)?.name ?? slug.replaceAll("_", " ");
    return [...bySector.entries()].map(([slug, list]) => ({ slug, title: nameOf(slug), items: list }));
  }, [sectionItems, taxonomy]);

  const meta = lensMeta(lens);

  return (
    <div className="mx-auto max-w-[1040px] px-5 pb-20 pt-7">
      <div className="mb-[18px] flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[30px] font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            Your feed
          </h1>
          <p className="mt-[5px] text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
            {meta.tagline}.{" "}
            <Link href="/interests" className="underline underline-offset-[3px]" style={{ color: "var(--ink-faint)" }}>
              Edit interests
            </Link>
          </p>
        </div>
        <div className="max-w-full overflow-x-auto">
          <div className="flex w-max gap-1 rounded-full border p-1" style={{ borderColor: "var(--line)" }} role="tablist" aria-label="Lens">
            {LENS_ORDER.map((slug) => {
              const m = lensMeta(slug);
              return (
                <Pill key={slug} selected={lens === slug} color={m.color} bg={m.bg} onClick={() => switchLens(slug)}>
                  {m.short}
                </Pill>
              );
            })}
            <span
              title="More lenses are on the way"
              className="rounded-full border border-dashed px-3 py-1.5 text-xs font-semibold"
              style={{ borderColor: "var(--line-strong)", color: "var(--ink-faint)" }}
            >
              + Soon
            </span>
          </div>
        </div>
      </div>

      <div className="mb-[26px] flex flex-wrap items-center gap-2">
        {profile?.region && (
          <div className="flex gap-0.5 rounded-full border p-1" style={{ borderColor: "var(--line)" }} role="tablist" aria-label="Scope">
            {(
              [
                ["all", "All"],
                ["region", regionName(profile.region)],
                ["world", "World"],
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
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-[18px]" style={{ background: "var(--bg-sunken)" }} />
          ))}
        </div>
      )}

      {!error && visible !== null && visible.length === 0 && (
        <div className="rounded-[18px] border p-[26px] text-sm" style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}>
          No stories here yet — widen your interests or check back shortly.
        </div>
      )}

      {!error && visible !== null && visibleTop.length > 0 && (
        <section className="mb-9">
          <div className="mb-3.5 flex items-baseline gap-3">
            <h2 className="text-[21px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
              Top stories
            </h2>
            <span className="spectrum-bar h-0.5 flex-1 rounded-sm opacity-50" />
          </div>
          <div className="stagger grid gap-4 sm:grid-cols-2 lg:grid-cols-3" key={`top-${lens}-${scope}`}>
            {visibleTop.map((item) => (
              <TopStoryCard key={item.id} item={item} lens={lens} />
            ))}
          </div>
        </section>
      )}

      {!error &&
        sections.map((sec) => (
          <section key={sec.slug} className="mb-9">
            <div className="mb-3.5 flex items-baseline gap-3">
              <Link
                href={`/sector/${sec.slug}`}
                className="text-[21px] font-semibold"
                style={{ fontFamily: "var(--font-display), serif", color: "var(--ink)" }}
              >
                {sec.title}
              </Link>
              <span className="h-px flex-1" style={{ background: "var(--line)" }} />
              <Link href={`/sector/${sec.slug}`} className="text-xs font-semibold" style={{ color: "var(--ink-faint)" }}>
                View sector →
              </Link>
            </div>
            <div className="flex flex-col gap-3">
              {sec.items.map((item) => (
                <StoryRowCard key={item.id} item={item} lens={lens} />
              ))}
            </div>
          </section>
        ))}
    </div>
  );
}
