"use client";

import Link from "next/link";
import { use, useEffect, useMemo, useState } from "react";
import { StoryRowCard } from "@/components/StoryCard";
import { useTaxonomy } from "@/components/ProfileEditor";
import { fetchFeed, type FeedItem } from "@/lib/api";
import { loadProfile } from "@/lib/profile";

export default function SectorPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const taxonomy = useTaxonomy();
  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [filter, setFilter] = useState<string | null>(null);
  const [lens, setLens] = useState("general");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const p = loadProfile();
    if (p?.lens) setLens(p.lens);
    fetchFeed({ sector: slug, region: p?.region, sort: "latest", limit: 50 })
      .then(setItems)
      .catch(() => setError("The Prism API is unreachable right now. Refresh in a moment."));
  }, [slug]);

  const sec = taxonomy.find((s) => s.slug === slug);
  const title = sec?.name ?? slug.replaceAll("_", " ");
  const visible = useMemo(
    () => (items ?? []).filter((i) => !filter || i.subsector === filter),
    [items, filter]
  );

  return (
    <div className="mx-auto max-w-[1200px] px-5 pb-20 pt-7 sm:px-8">
      <Link href="/feed" className="mb-[18px] block text-[12.5px] font-semibold" style={{ color: "var(--ink-faint)" }}>
        ← Back to feed
      </Link>
      <h1 className="text-[30px] font-semibold capitalize tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        {title}
      </h1>
      <p className="mt-1.5 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
        {visible.length} stor{visible.length === 1 ? "y" : "ies"} · origin-balanced, blindspots flagged
      </p>

      <div className="mb-[26px] mt-5 flex flex-wrap gap-2">
        {[{ slug: null as string | null, name: `All ${title.toLowerCase()}` }, ...(sec?.subsectors ?? [])].map((f) => {
          const val = typeof f.slug === "string" ? f.slug : null;
          const sel = filter === val;
          return (
            <button
              key={val ?? "all"}
              onClick={() => setFilter(val)}
              className="rounded-full border px-[15px] py-[7px] text-[12.5px] font-semibold transition"
              style={{
                borderColor: sel ? "var(--ink)" : "var(--line)",
                background: sel ? "var(--ink)" : "var(--bg-elevated)",
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
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-[18px]" style={{ background: "var(--bg-sunken)" }} />
          ))}
        </div>
      )}
      {!error && items !== null && visible.length === 0 && (
        <div className="rounded-[18px] border p-[26px] text-sm" style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}>
          No stories in this sub-domain yet — check back shortly.
        </div>
      )}
      <div className="stagger flex flex-col gap-3" key={`${slug}-${filter ?? "all"}`}>
        {visible.map((item) => (
          <StoryRowCard key={item.id} item={item} lens={lens} />
        ))}
      </div>
    </div>
  );
}
