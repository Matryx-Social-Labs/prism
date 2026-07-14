import Link from "next/link";
import { fetchFeed, type FeedItem } from "@/lib/api";

export const dynamic = "force-dynamic";

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const hours = Math.floor(diffMs / 3_600_000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function SeverityBadge({ item }: { item: FeedItem }) {
  if (item.cvss_score == null) return null;
  const severity = item.cvss_severity ?? (item.cvss_score >= 9 ? "critical" : item.cvss_score >= 7 ? "high" : "medium");
  const colors: Record<string, string> = {
    critical: "bg-red-600 text-white",
    high: "bg-orange-600 text-white",
    medium: "bg-amber-500 text-white",
    low: "bg-lime-600 text-white",
  };
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${colors[severity] ?? "bg-stone-500 text-white"}`}>
      CVSS {item.cvss_score.toFixed(1)}
    </span>
  );
}

export default async function FeedPage() {
  let items: FeedItem[] = [];
  let error: string | null = null;
  try {
    items = await fetchFeed();
  } catch {
    error = "The Prism API is unreachable. Start the backend and refresh.";
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold">Your feed</h1>
      <p className="mb-6 text-sm text-stone-500">
        Ranked for a security &amp; GRC role: severity, active exploitation, recency, corroboration.
      </p>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {error}
        </div>
      )}

      {!error && items.length === 0 && (
        <div className="rounded-lg border border-stone-200 p-6 text-sm text-stone-500 dark:border-stone-800">
          No events yet — the pipeline is still ingesting. Refresh in a minute.
        </div>
      )}

      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.id}>
            <Link
              href={`/story/${item.id}`}
              className="block rounded-lg border border-stone-200 p-4 transition hover:border-stone-400 dark:border-stone-800 dark:hover:border-stone-600"
            >
              <div className="mb-1.5 flex flex-wrap items-center gap-2">
                <SeverityBadge item={item} />
                {item.kev_listed && (
                  <span className="rounded bg-red-700 px-1.5 py-0.5 text-xs font-semibold text-white">
                    ⚠ Actively exploited
                  </span>
                )}
                {item.cve_ids.map((cve) => (
                  <span key={cve} className="rounded bg-stone-200 px-1.5 py-0.5 font-mono text-xs dark:bg-stone-800">
                    {cve}
                  </span>
                ))}
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
