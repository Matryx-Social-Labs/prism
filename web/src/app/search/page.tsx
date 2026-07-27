"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StoryRowCard } from "@/components/StoryCard";
import { fetchTrending, searchEvents, type FeedItem } from "@/lib/api";
import { useScrollRestore } from "@/lib/useScrollRestore";

function SearchInner() {
  const params = useSearchParams();
  const router = useRouter();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [results, setResults] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  // A rejected search is NOT the same as no results. Without this the page went
  // completely blank on a failed request: `searched` stays false because it is
  // set after the await, `loading` is false, `results` is empty, and a term of 2+
  // characters hides the start screen — so every render branch was false and the
  // reader got nothing to read and nothing to do.
  const [failed, setFailed] = useState(false);
  // Which term produced `results`. Without it, a new query inherits the
  // previous query's results as "ready" and restores that key's offset
  // before its own results exist.
  const [resultsTerm, setResultsTerm] = useState("");
  // Real entities off the live trending cast — a hardcoded list would go stale
  // and, on a product that sells provenance, would be quietly dishonest.
  const [entities, setEntities] = useState<string[]>([]);

  useEffect(() => {
    fetchTrending({ limit: 6 })
      .then((s) => setEntities([...new Set(s.flatMap((x) => x.cast ?? []))].slice(0, 6)))
      .catch(() => setEntities([]));
  }, []);

  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) {
      setResults([]);
      setSearched(false);
      setFailed(false);
      // Clearing the box while a request is still in flight used to strand
      // `loading` at true: the cleanup below cancels, and the in-flight finally
      // is guarded by `if (!cancelled)` so it never resets it. The reader was
      // left on "Searching…" forever, with the start screen hidden behind the
      // same !loading gate — an empty box that never came back.
      setLoading(false);
      return;
    }
    setLoading(true);
    setFailed(false);
    // clearTimeout cancels the timer, not an in-flight request — without the
    // flag a slow response for an abandoned query overwrites a newer one.
    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const items = await searchEvents(term);
        if (cancelled) return;
        setResults(items);
        setResultsTerm(term);
        setSearched(true);
        router.replace(`/search?q=${encodeURIComponent(term)}`, { scroll: false });
      } catch {
        // A network failure REJECTS (searchEvents only swallows !res.ok), and an
        // escaped rejection left setLoading(true) — "Searching…" forever, which
        // is the common case on a flaky mobile connection.
        if (!cancelled) {
          setResults([]);
          setFailed(true);
        }
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
  useScrollRestore(`search:${q.trim()}:scrollY`, resultsTerm === q.trim() && results.length > 0);

  const term = q.trim();

  return (
    <div className="mx-auto w-full max-w-[760px] px-5 pb-28 pt-9 lg:max-w-[1240px] lg:px-10">
      {/* The query sets in the display voice — the thing you typed is the headline
          of this screen (Parse Desktop.dc.html). */}
      <input
        autoFocus
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => e.key === "Escape" && setQ("")}
        placeholder="Search"
        aria-label="Search stories, entities and sources"
        className="w-full border-0 bg-transparent p-0 text-[28px] leading-tight tracking-[-0.02em] outline-none placeholder:opacity-40 sm:text-[34px]"
        style={{ fontFamily: "var(--font-display), serif", fontWeight: 400, color: "var(--ink)" }}
      />
      <div className="mt-3 border-b" style={{ borderColor: "var(--line)" }} />

      {/* What is searchable, in the provenance voice. */}
      <p className="mt-2.5 font-mono text-[10.5px] uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
        stories · entities · tickers · CVE ids
      </p>

      {/* EMPTY STATE — the screen used to be blank until you typed, which is the
          emptiest surface in the app. Give the reader somewhere to start. */}
      {term.length < 2 && !loading && (
        <div className="mt-8 flex flex-col gap-8 lg:flex-row lg:gap-16">
          <div className="min-w-0 flex-1">
            <p className="font-mono text-[10.5px] uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
              Trending entities
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {entities.map((e) => (
                <button
                  key={e}
                  onClick={() => setQ(e)}
                  className="rounded-full border px-3 py-[7px] text-[13px] transition hover:opacity-70"
                  style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
                >
                  {e}
                </button>
              ))}
            </div>
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-mono text-[10.5px] uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
              Try
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {["RELIANCE", "CVE-2026-62144", "Kerala"].map((t) => (
                <button
                  key={t}
                  onClick={() => setQ(t)}
                  className="rounded-full border px-3 py-[7px] font-mono text-[11.5px] transition hover:opacity-70"
                  style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="mt-6 flex flex-col gap-3">
        {loading && (
          <p className="text-[13.5px]" style={{ color: "var(--ink-faint)" }}>
            Searching…
          </p>
        )}
        {!loading && failed && (
          <p className="text-[14px]" style={{ color: "var(--ink-muted)" }} role="status">
            Search is unreachable right now — check your connection and try again.
          </p>
        )}
        {!loading && !failed && searched && results.length === 0 && (
          <p className="text-[14px]" style={{ color: "var(--ink-muted)" }}>
            No stories match “{term}”.
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
