"use client";

import Link from "next/link";
import { use, useEffect, useMemo, useState } from "react";
import { StoryRowCard } from "@/components/StoryCard";
import { useTaxonomy } from "@/components/ProfileEditor";
import { fetchFeed, type FeedItem } from "@/lib/api";
import { useLenses } from "@/lib/lenses";
import { loadProfile } from "@/lib/profile";
import { useScrollRestore } from "@/lib/useScrollRestore";

export default function SectorPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const taxonomy = useTaxonomy();
  const lenses = useLenses();
  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [filter, setFilter] = useState<string | null>(null);
  const [lens, setLens] = useState("reader");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const p = loadProfile();
    if (p?.lens) setLens(p.lens);
    // Slug changes are user-driven and rapid (the sector rail is a list of
    // links), so without this a slow response for sector A lands after B and
    // renders A's stories under B's heading. Resetting items/error also stops
    // the previous sector's list showing under the new title, and stops one
    // transient failure pinning the error banner for every later sector.
    let cancelled = false;
    setItems(null);
    setError(null);
    fetchFeed({ sector: slug, region: p?.region, sort: "latest", limit: 50 })
      .then((list) => {
        if (!cancelled) setItems(list);
      })
      .catch(() => {
        if (!cancelled) setError("The Parse API is unreachable right now. Refresh in a moment.");
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  useScrollRestore(`sector:${slug}:scrollY`, items !== null);

  const sec = taxonomy.find((s) => s.slug === slug);
  const title = sec?.name ?? slug.replaceAll("_", " ");
  const visible = useMemo(
    () => (items ?? []).filter((i) => !filter || i.subsector === filter),
    [items, filter]
  );

  return (
    <div className="mx-auto grid max-w-[1240px] items-start gap-8 px-5 pb-24 pt-6 sm:px-8 lg:grid-cols-[200px_1fr] lg:pb-20 xl:px-10">
      {/* Sections rail — carries over from the feed. Hidden on mobile. */}
      <aside className="sticky top-[72px] hidden flex-col gap-0.5 lg:flex">
        <span
          className="px-3 pb-2 text-[10.5px] font-semibold uppercase tracking-[0.14em]"
          style={{ color: "var(--ink-faint)" }}
        >
          Sections
        </span>
        {[
          { href: "/feed", label: "For you" },
          { href: "/feed", label: "Top stories" },
        ].map((r) => (
          <Link
            key={r.label}
            href={r.href}
            className="rounded-[10px] px-3 py-2 text-[13.5px] font-medium transition"
            style={{ color: "var(--ink-muted)" }}
          >
            {r.label}
          </Link>
        ))}
        <span className="mx-3 my-2 h-px" style={{ background: "var(--line)" }} />
        {taxonomy.map((s) => {
          const active = s.slug === slug;
          return (
            <Link
              key={s.slug}
              href={`/sector/${s.slug}`}
              className="flex items-center justify-between rounded-[10px] px-3 py-2 text-[13.5px] transition"
              style={{
                fontWeight: active ? 600 : 500,
                color: active ? "var(--ink)" : "var(--ink-muted)",
                background: active ? "var(--bg-sunken)" : "transparent",
              }}
            >
              <span>{s.name}</span>
              {active && items !== null && (
                <span className="text-[10.5px]" style={{ fontFamily: "var(--font-mono), monospace", color: "var(--ink-faint)" }}>
                  {visible.length}
                </span>
              )}
            </Link>
          );
        })}
      </aside>

      <div>
        <div className="mb-2 flex items-center justify-between gap-3">
          <h1 className="text-[26px] font-semibold capitalize tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            {title}
          </h1>
          {/* Lens pills */}
          <div className="flex gap-1 rounded-full border p-1" style={{ borderColor: "var(--line)" }} role="tablist" aria-label="Lens">
            {lenses.map((m) => {
              const sel = lens === m.slug;
              return (
                <button
                  key={m.slug}
                  role="tab"
                  aria-selected={sel}
                  onClick={() => setLens(m.slug)}
                  className="whitespace-nowrap rounded-full px-[13px] py-[5px] text-xs font-semibold transition"
                  style={
                    sel
                      ? { background: m.bg, color: m.color, boxShadow: `inset 0 0 0 1.5px ${m.color}` }
                      : { color: "var(--ink-muted)" }
                  }
                >
                  {m.short}
                </button>
              );
            })}
          </div>
        </div>

        {/* Subsector chips — on mobile this is the horizontal scroll rail. */}
        <div className="mb-[18px] -mx-5 flex gap-1.5 overflow-x-auto px-5 pb-1 sm:-mx-8 sm:px-8 lg:mx-0 lg:flex-wrap lg:overflow-visible lg:px-0">
          {[{ slug: null as string | null, name: "All" }, ...(sec?.subsectors ?? [])].map((f) => {
            const val = typeof f.slug === "string" ? f.slug : null;
            const sel = filter === val;
            return (
              <button
                key={val ?? "all"}
                onClick={() => setFilter(val)}
                className="whitespace-nowrap rounded-full border px-[14px] py-1.5 text-xs font-semibold transition"
                style={{
                  borderColor: sel ? "var(--ink)" : "var(--line)",
                  background: sel ? "var(--ink)" : "transparent",
                  color: sel ? "var(--bg)" : "var(--ink-muted)",
                }}
              >
                {f.name}
              </button>
            );
          })}
        </div>

        {error && (
          <div className="rounded-[18px] border p-5 text-sm" style={{ borderColor: "var(--danger)", background: "var(--danger-bg)", color: "var(--danger)" }}>
            {error}
          </div>
        )}
        {!error && items === null && (
          <div className="space-y-2.5">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-24 animate-pulse rounded-2xl" style={{ background: "var(--bg-sunken)" }} />
            ))}
          </div>
        )}
        {!error && items !== null && visible.length === 0 && (
          <div className="rounded-[18px] border p-[26px] text-sm" style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}>
            No stories in this sub-domain yet — check back shortly.
          </div>
        )}
        <div className="stagger flex flex-col gap-2.5" key={`${slug}-${filter ?? "all"}`}>
          {visible.map((item) => (
            <StoryRowCard key={item.id} item={item} lens={lens} />
          ))}
        </div>
      </div>
    </div>
  );
}
