"use client";

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
    <div className="mx-auto max-w-[820px] px-5 pb-24 pt-8 sm:px-8">
      <h1 className="text-[30px] font-semibold leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        Trending now
      </h1>
      <p className="mt-2 text-[14px]" style={{ color: "var(--ink-muted)" }}>
        The stories the most outlets are covering right now — each a whole story, start to now.
      </p>

      {tabs.length > 1 && (
        <div className="mt-5 flex gap-2">
          {tabs.map((t) => (
            <button
              key={t.k}
              onClick={() => setScope(t.k as "local" | "india")}
              className="min-h-[36px] rounded-full border px-4 text-[13px] font-medium transition"
              style={{
                borderColor: scope === t.k ? "var(--ink)" : "var(--line-strong)",
                background: scope === t.k ? "var(--ink)" : "transparent",
                color: scope === t.k ? "var(--bg)" : "var(--ink)",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
      )}

      <div className="mt-7 flex flex-col divide-y" style={{ borderColor: "var(--line)" }}>
        {stories === null ? (
          <p className="py-8 text-[13px]" style={{ color: "var(--ink-faint)" }}>Loading…</p>
        ) : stories.length === 0 ? (
          <p className="py-8 text-[13px]" style={{ color: "var(--ink-faint)" }}>
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
    <Link href={`/trending/${story.slug}`} className="flex items-start gap-4 py-4" style={{ borderColor: "var(--line)" }}>
      <span className="mt-0.5 w-6 shrink-0 text-[15px] font-semibold" style={{ color: "var(--ink-faint)", fontFamily: "var(--font-mono), monospace" }}>
        {rank}
      </span>
      {story.hero_image && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={story.hero_image} alt="" width={72} height={72} className="h-[72px] w-[72px] shrink-0 rounded-[10px] object-cover" />
      )}
      <div className="min-w-0 flex-1">
        <p className="text-[16px] font-semibold leading-snug" style={{ fontFamily: "var(--font-display), serif" }}>
          {story.label}
        </p>
        <p className="mt-1.5 text-[11px] uppercase tracking-[0.08em]" style={{ color: "var(--ink-faint)", fontFamily: "var(--font-mono), monospace" }}>
          {story.source_count} outlets · {story.developments} developments
          {story.velocity > 0 ? " · developing now" : ""}
        </p>
      </div>
    </Link>
  );
}

function stateLabel(code: string): string {
  return { "IN-KA": "Karnataka", "IN-TN": "Tamil Nadu", "IN-MH": "Maharashtra", "IN-DL": "Delhi", "IN-KL": "Kerala", "IN-TG": "Telangana", "IN-AP": "Andhra" }[code] ?? code;
}
