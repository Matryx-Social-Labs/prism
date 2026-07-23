"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { fetchTrending, type TrendingStory } from "@/lib/api";
import { loadProfile } from "@/lib/profile";

export default function TrendingPage() {
  const [state, setState] = useState<string | null>(null);
  const [scope, setScope] = useState<"local" | "india">("india");
  const [stories, setStories] = useState<TrendingStory[] | null>(null);

  useEffect(() => {
    const p = loadProfile();
    if (p?.state) {
      setState(p.state);
      setScope("local"); // default to the reader's area when we know it
    }
  }, []);

  useEffect(() => {
    setStories(null);
    fetchTrending({ state: scope === "local" ? state : null, limit: 24 })
      .then(setStories)
      .catch(() => setStories([]));
  }, [scope, state]);

  const tabs = useMemo(
    () => (state ? [{ k: "local", label: stateLabel(state) }, { k: "india", label: "India" }] : [{ k: "india", label: "India" }]),
    [state],
  );

  return (
    <div className="mx-auto max-w-[720px] px-8 pb-24 pt-10">
      <h1 className="text-[30px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
        Trending now
      </h1>
      <p className="mt-2 text-[14px]" style={{ color: "var(--ink-muted)" }}>
        The stories the most outlets are covering right now — each a whole story, start to now.
      </p>

      {tabs.length > 1 && (
        <div className="mt-5 flex gap-2">
          {tabs.map((t) => {
            const active = scope === t.k;
            return (
              <button
                key={t.k}
                onClick={() => setScope(t.k as "local" | "india")}
                className="rounded-full border px-[18px] py-2 text-[13px] font-semibold transition"
                style={{
                  borderColor: active ? "var(--ink)" : "var(--line-strong)",
                  background: active ? "var(--ink)" : "transparent",
                  color: active ? "var(--bg)" : "var(--ink)",
                }}
              >
                {t.label}
              </button>
            );
          })}
        </div>
      )}

      <div className="mt-5 flex flex-col">
        {stories === null ? (
          [0, 1, 2, 3, 4].map((i) => <SkeletonRow key={i} />)
        ) : stories.length === 0 ? (
          <p className="py-4 text-[13px]" style={{ color: "var(--ink-faint)" }}>
            No trending stories here right now — check back soon.
          </p>
        ) : (
          stories.map((s, i) => <StoryRow key={s.slug} story={s} rank={i + 1} />)
        )}
      </div>
    </div>
  );
}

function StoryRow({ story, rank }: { story: TrendingStory; rank: number }) {
  return (
    <Link
      href={`/trending/${story.slug}`}
      className="flex items-start gap-4 border-b py-4"
      style={{ borderColor: "var(--line)" }}
    >
      <span
        className="w-6 shrink-0 text-[15px] font-semibold"
        style={{ color: "var(--ink-faint)", fontFamily: "var(--font-mono), monospace" }}
      >
        {rank}
      </span>
      <span
        className="relative block h-[72px] w-[72px] shrink-0 overflow-hidden rounded-[10px]"
        style={{ background: "var(--bg-sunken)" }}
      >
        {story.hero_image && (
          <Image
            src={story.hero_image}
            alt=""
            fill
            sizes="72px"
            className="object-cover"
            onError={(e) => {
              (e.currentTarget as HTMLElement).style.display = "none";
            }}
          />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[16px] font-semibold leading-[1.4]" style={{ fontFamily: "var(--font-display), serif" }}>
          {story.label}
        </p>
        <p
          className="mt-1.5 text-[11px] uppercase tracking-[0.08em]"
          style={{ color: "var(--ink-faint)", fontFamily: "var(--font-mono), monospace" }}
        >
          {story.source_count} outlets · {story.developments} developments
          {story.velocity > 0 && (
            <>
              {" · "}
              <span style={{ color: "var(--up)" }}>developing now</span>
            </>
          )}
        </p>
      </div>
    </Link>
  );
}

function SkeletonRow() {
  return (
    <div className="flex items-start gap-4 border-b py-4" style={{ borderColor: "var(--line)" }}>
      <span className="w-6 shrink-0" />
      <span className="block h-[72px] w-[72px] shrink-0 animate-pulse rounded-[10px]" style={{ background: "var(--bg-sunken)" }} />
      <div className="min-w-0 flex-1 space-y-2 pt-1">
        <span className="block h-[14px] w-3/4 animate-pulse rounded" style={{ background: "var(--bg-sunken)" }} />
        <span className="block h-[10px] w-2/5 animate-pulse rounded" style={{ background: "var(--bg-sunken)" }} />
      </div>
    </div>
  );
}

function stateLabel(code: string): string {
  return { "IN-KA": "Karnataka", "IN-TN": "Tamil Nadu", "IN-MH": "Maharashtra", "IN-DL": "Delhi", "IN-KL": "Kerala", "IN-TG": "Telangana", "IN-AP": "Andhra" }[code] ?? code;
}
