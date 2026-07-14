"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchFeed, fetchLenses, type FeedItem, type LensInfo } from "@/lib/api";
import { loadProfile, saveProfile } from "@/lib/profile";

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const hours = Math.floor(diffMs / 3_600_000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function Badges({ item }: { item: FeedItem }) {
  const severity =
    item.cvss_severity ??
    (item.cvss_score != null ? (item.cvss_score >= 9 ? "critical" : item.cvss_score >= 7 ? "high" : "medium") : null);
  const severityColors: Record<string, string> = {
    critical: "bg-red-600 text-white",
    high: "bg-orange-600 text-white",
    medium: "bg-amber-500 text-white",
    low: "bg-lime-600 text-white",
  };
  return (
    <>
      {item.cvss_score != null && (
        <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${severityColors[severity ?? ""] ?? "bg-stone-500 text-white"}`}>
          CVSS {item.cvss_score.toFixed(1)}
        </span>
      )}
      {item.kev_listed && (
        <span className="rounded bg-red-700 px-1.5 py-0.5 text-xs font-semibold text-white">⚠ Actively exploited</span>
      )}
      {item.cve_ids.map((cve) => (
        <span key={cve} className="rounded bg-stone-200 px-1.5 py-0.5 font-mono text-xs dark:bg-stone-800">{cve}</span>
      ))}
      {item.tickers.map((t) => (
        <span key={t} className="rounded bg-indigo-100 px-1.5 py-0.5 font-mono text-xs font-semibold text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300">
          ${t}
        </span>
      ))}
      {item.catalyst && (
        <span className="rounded bg-stone-100 px-1.5 py-0.5 text-xs text-stone-600 dark:bg-stone-900 dark:text-stone-400">
          {item.catalyst.replaceAll("_", " ")}
        </span>
      )}
      {item.price_impact_direction && (
        <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${
          item.price_impact_direction === "up"
            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
            : item.price_impact_direction === "down"
              ? "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"
              : "bg-stone-100 text-stone-600 dark:bg-stone-900 dark:text-stone-400"
        }`}>
          {item.price_impact_direction === "up" ? "▲" : item.price_impact_direction === "down" ? "▼" : "◆"} price
        </span>
      )}
    </>
  );
}

export default function FeedPage() {
  const [lens, setLens] = useState<string>("cyber_grc");
  const [lenses, setLenses] = useState<LensInfo[]>([]);
  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const profile = loadProfile();
    if (profile) setLens(profile.lens);
    fetchLenses().then(setLenses);
  }, []);

  useEffect(() => {
    setItems(null);
    setError(null);
    fetchFeed(lens)
      .then(setItems)
      .catch(() => setError("The Prism API is unreachable. Start the backend and refresh."));
  }, [lens]);

  function switchLens(slug: string) {
    setLens(slug);
    saveProfile({ lens: slug });
  }

  const activeLens = lenses.find((l) => l.slug === lens);

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Your feed</h1>
          <p className="text-sm text-stone-500">{activeLens?.tagline ?? "Ranked for your role."}</p>
        </div>
        <div className="flex gap-1 rounded-lg border border-stone-200 p-1 dark:border-stone-800">
          {(lenses.length ? lenses : [{ slug: "cyber_grc", name: "Cyber/GRC", tagline: "" }]).map((l) => (
            <button
              key={l.slug}
              onClick={() => switchLens(l.slug)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                lens === l.slug
                  ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900"
                  : "text-stone-600 hover:bg-stone-100 dark:text-stone-400 dark:hover:bg-stone-900"
              }`}
            >
              {l.name}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {error}
        </div>
      )}

      {!error && items === null && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg bg-stone-100 dark:bg-stone-900" />
          ))}
        </div>
      )}

      {!error && items !== null && items.length === 0 && (
        <div className="rounded-lg border border-stone-200 p-6 text-sm text-stone-500 dark:border-stone-800">
          No stories for this lens yet — the pipeline may still be ingesting. Check back shortly.
        </div>
      )}

      <ul className="space-y-3">
        {(items ?? []).map((item) => (
          <li key={item.id}>
            <Link
              href={`/story/${item.id}`}
              className="block rounded-lg border border-stone-200 p-4 transition hover:border-stone-400 dark:border-stone-800 dark:hover:border-stone-600"
            >
              <div className="mb-1.5 flex flex-wrap items-center gap-2">
                <Badges item={item} />
                <span className="ml-auto text-xs text-stone-400">
                  {item.source_count} source{item.source_count === 1 ? "" : "s"} · {timeAgo(item.last_updated_at)}
                </span>
              </div>
              <h2 className="font-semibold leading-snug">{item.title}</h2>
              {item.summary && (
                <p className="mt-1 line-clamp-2 text-sm text-stone-600 dark:text-stone-400">{item.summary}</p>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
