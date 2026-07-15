"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchFeed, type FeedItem } from "@/lib/api";
import { LENS_ORDER, lensMeta } from "@/lib/lenses";
import { loadProfile, saveProfile } from "@/lib/profile";

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const hours = Math.floor(diffMs / 3_600_000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function Badges({ item, lens }: { item: FeedItem; lens: string }) {
  return (
    <>
      {lens === "general" && item.sector && (
        <span className="rounded-full px-2 py-0.5 text-xs font-semibold uppercase tracking-wide" style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}>
          {item.sector}
        </span>
      )}
      {item.cvss_score != null && (
        <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={{ background: "var(--danger-bg)", color: "var(--danger)" }}>
          CVSS {item.cvss_score.toFixed(1)}
        </span>
      )}
      {item.kev_listed && (
        <span className="rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ background: "var(--danger)" }}>
          ⚠ Actively exploited
        </span>
      )}
      {item.cve_ids.slice(0, 2).map((cve) => (
        <span key={cve} className="rounded-full px-2 py-0.5 font-mono text-xs" style={{ background: "var(--bg-sunken)" }}>
          {cve}
        </span>
      ))}
      {item.tickers.map((t) => (
        <span key={t} className="rounded-full px-2 py-0.5 font-mono text-xs font-semibold" style={{ background: "var(--lens-finance-bg)", color: "var(--lens-finance)" }}>
          ${t}
        </span>
      ))}
      {item.catalyst && (
        <span className="rounded-full px-2 py-0.5 text-xs" style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}>
          {item.catalyst.replaceAll("_", " ")}
        </span>
      )}
      {item.price_impact_direction && (
        <span
          className="rounded-full px-2 py-0.5 text-xs font-semibold"
          style={
            item.price_impact_direction === "up"
              ? { background: "var(--up-bg)", color: "var(--up)" }
              : item.price_impact_direction === "down"
                ? { background: "var(--danger-bg)", color: "var(--danger)" }
                : { background: "var(--bg-sunken)", color: "var(--ink-muted)" }
          }
        >
          {item.price_impact_direction === "up" ? "▲" : item.price_impact_direction === "down" ? "▼" : "◆"} price
        </span>
      )}
    </>
  );
}

export default function FeedPage() {
  const [lens, setLens] = useState<string>("general");
  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const profile = loadProfile();
    if (profile?.lens) setLens(profile.lens);
  }, []);

  useEffect(() => {
    setItems(null);
    setError(null);
    fetchFeed(lens)
      .then(setItems)
      .catch(() => setError("The Prism API is unreachable right now. Refresh in a moment."));
  }, [lens]);

  function switchLens(slug: string) {
    setLens(slug);
    saveProfile({ lens: slug });
  }

  const meta = lensMeta(lens);

  return (
    <div>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            Your feed
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
            {meta.tagline}.
          </p>
        </div>
        <div className="flex gap-1 rounded-full border p-1" style={{ borderColor: "var(--line)" }} role="tablist" aria-label="Lens">
          {LENS_ORDER.map((slug) => {
            const m = lensMeta(slug);
            const selected = lens === slug;
            return (
              <button
                key={slug}
                role="tab"
                aria-selected={selected}
                onClick={() => switchLens(slug)}
                className="rounded-full px-3.5 py-1.5 text-xs font-semibold transition"
                style={
                  selected
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

      {error && (
        <div className="rounded-2xl border p-5 text-sm" style={{ borderColor: "var(--danger)", background: "var(--danger-bg)", color: "var(--danger)" }}>
          {error}
        </div>
      )}

      {!error && items === null && (
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-2xl" style={{ background: "var(--bg-sunken)" }} />
          ))}
        </div>
      )}

      {!error && items !== null && items.length === 0 && (
        <div className="rounded-2xl border p-6 text-sm" style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}>
          No stories for this lens yet — the pipeline may still be ingesting. Check back shortly.
        </div>
      )}

      <ul className="stagger space-y-3" key={lens}>
        {(items ?? []).map((item) => (
          <li key={item.id}>
            <Link
              href={`/story/${item.id}`}
              className="card-hover block rounded-2xl border p-5"
              style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
            >
              <div className="mb-2 flex flex-wrap items-center gap-1.5">
                <Badges item={item} lens={lens} />
                <span className="ml-auto text-xs" style={{ color: "var(--ink-faint)" }}>
                  {item.source_count} source{item.source_count === 1 ? "" : "s"} · {timeAgo(item.last_updated_at)}
                </span>
              </div>
              <h2 className="font-semibold leading-snug">{item.title}</h2>
              {item.summary && (
                <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed" style={{ color: "var(--ink-muted)" }}>
                  {item.summary}
                </p>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
