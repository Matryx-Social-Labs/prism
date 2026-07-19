"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StoryRowCard } from "@/components/StoryCard";
import { searchEvents, type FeedItem } from "@/lib/api";

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
    const t = setTimeout(async () => {
      const items = await searchEvents(term);
      setResults(items);
      setLoading(false);
      setSearched(true);
      router.replace(`/search?q=${encodeURIComponent(term)}`, { scroll: false });
    }, 250);
    return () => clearTimeout(t);
  }, [q, router]);

  return (
    <main className="mx-auto w-full max-w-[760px] px-5 py-10">
      <h1 className="text-[28px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
        Search
      </h1>
      <input
        autoFocus
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search stories, companies, tickers…"
        aria-label="Search stories"
        className="mt-4 w-full rounded-[12px] border px-4 py-3 text-[15px] outline-none"
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
          <StoryRowCard key={item.id} item={item} lens="general" />
        ))}
      </div>
    </main>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={null}>
      <SearchInner />
    </Suspense>
  );
}
