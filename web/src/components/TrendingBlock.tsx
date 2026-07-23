"use client";

// Feed "Top Stories" block (Option A): trending communities as whole stories,
// not scattered headlines. Scoped by the reader's state with a geo toggle; each
// card opens the shareable /trending/<slug> permalink. Compact — the full list
// lives at /trending.
import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchTrending, type TrendingStory } from "@/lib/api";

export function TrendingBlock({ state }: { state?: string | null }) {
  const [scope, setScope] = useState<"local" | "india">(state ? "local" : "india");
  const [stories, setStories] = useState<TrendingStory[] | null>(null);

  useEffect(() => {
    setStories(null);
    fetchTrending({ state: scope === "local" && state ? state : null, limit: 5 })
      .then(setStories)
      .catch(() => setStories([]));
  }, [scope, state]);

  if (stories !== null && stories.length === 0) return null; // nothing trending → hide, no empty box

  return (
    <section className="mb-8">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)", fontFamily: "var(--font-mono), monospace" }}>
          Trending now
        </span>
        <div className="flex items-center gap-2">
          {state && (
            <div className="flex gap-1">
              {(["local", "india"] as const).map((k) => (
                <button
                  key={k}
                  onClick={() => setScope(k)}
                  className="rounded-full px-2.5 py-1 text-[11px] font-medium transition"
                  style={{ background: scope === k ? "var(--ink)" : "transparent", color: scope === k ? "var(--bg)" : "var(--ink-faint)" }}
                >
                  {k === "local" ? "Near me" : "India"}
                </button>
              ))}
            </div>
          )}
          <Link href="/trending" className="text-[12px] font-medium" style={{ color: "var(--ink-faint)" }}>
            See all →
          </Link>
        </div>
      </div>

      <div className="grid gap-2.5 sm:grid-cols-2">
        {(stories ?? []).slice(0, 4).map((s) => (
          <Link
            key={s.slug}
            href={`/trending/${s.slug}`}
            className="flex items-center gap-3 rounded-[14px] border px-3.5 py-3 transition hover:opacity-90"
            style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
          >
            {s.hero_image && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={s.hero_image} alt="" width={52} height={52} className="h-[52px] w-[52px] shrink-0 rounded-[9px] object-cover" />
            )}
            <div className="min-w-0">
              <p className="truncate text-[14px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
                {s.label}
              </p>
              <p className="mt-0.5 text-[10.5px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-faint)", fontFamily: "var(--font-mono), monospace" }}>
                {s.source_count} outlets · {s.developments} devs{s.velocity > 0 ? " · live" : ""}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
