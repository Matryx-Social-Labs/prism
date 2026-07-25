"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StoryRowCard } from "@/components/StoryCard";
import { searchEvents, type FeedItem } from "@/lib/api";
import { useScrollRestore } from "@/lib/useScrollRestore";

function SearchInner() {
  const params = useSearchParams();
  const router = useRouter();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [results, setResults] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) {
      setResults([]);
      setSearched(false);
      return;
    }
    setLoading(true);
    // clearTimeout cancels the timer, not an in-flight request — without the
    // flag a slow response for an abandoned query overwrites a newer one.
    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const items = await searchEvents(term);
        if (cancelled) return;
        setResults(items);
        setSearched(true);
        router.replace(`/search?q=${encodeURIComponent(term)}`, { scroll: false });
      } catch {
        // A network failure REJECTS (searchEvents only swallows !res.ok), and an
        // escaped rejection left setLoading(true) — "Searching…" forever, which
        // is the common case on a flaky mobile connection.
        if (!cancelled) setResults([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q, router]);

  // Keyed per query: with a route-wide key, the first results for a NEW search
  // would restore a previous search's offset and jump the page out from under
  // a reader who is still typing (the input autofocuses).
  useScrollRestore(`search:${q.trim()}:scrollY`, results.length > 0);

  return (
    <div className="mx-auto w-full max-w-[760px] px-5 pb-28 pt-9">
      <h1 className="text-[28px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
        Search
      </h1>
      <input
        autoFocus
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search stories, companies, tickers…"
        aria-label="Search stories"
        className="mt-4 w-full rounded-[12px] border px-4 py-3 text-[16px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1"
        style={{ borderColor: "var(--line-strong)", background: "var(--bg)", color: "var(--ink)" }}
      />

      <div className="mt-6 flex flex-col gap-3">
        {loading && (
          <p className="text-[13.5px]" style={{ color: "var(--ink-faint)" }}>
            Searching…
          </p>
        )}
        {!loading && searched && results.length === 0 && (
          <p className="text-[14px]" style={{ color: "var(--ink-muted)" }}>
            No stories match “{q.trim()}”.
          </p>
        )}
        {results.map((item) => (
          <StoryRowCard key={item.id} item={item} lens="reader" />
        ))}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={null}>
      <SearchInner />
    </Suspense>
  );
}
