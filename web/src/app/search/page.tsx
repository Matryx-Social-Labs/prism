"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChartRow } from "@/components/ChartRow";
import { Masthead } from "@/components/Masthead";
import { SectorStrip } from "@/components/SectorStrip";
import { EmptyState } from "@/components/tabs/EmptyState";
import { fetchTrending, searchEvents, type FeedItem } from "@/lib/api";
import { chartOrder } from "@/lib/chart";
import { loadProfile } from "@/lib/profile";
import { sectorGroup } from "@/lib/sectors";
import { useScrollRestore } from "@/lib/useScrollRestore";

/**
 * Search (Design System v2 · reader-phone PhoneSearch): the query field first,
 * a mono strip under it that says what can be searched or counts what came
 * back, then results on the story row grammar, most-corroborated first; the
 * subject nav filters them in place. The start screen offers only what is in
 * the news now — real names off the live stories — and nothing when that list
 * is empty. A failed request says so, in its own line — never "no matches"
 * for an error.
 */
function SearchInner() {
  const params = useSearchParams();
  const router = useRouter();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [results, setResults] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  // A rejected search is NOT the same as no results: without this flag every
  // render branch was false on a failed request and the page went blank.
  const [failed, setFailed] = useState(false);
  // Which term produced `results`, so a new query never restores the previous
  // query's scroll offset before its own results exist.
  const [resultsTerm, setResultsTerm] = useState("");
  const [group, setGroup] = useState<string | null>(null);
  const [primaryLang, setPrimaryLang] = useState("en");
  // Real entities off the live trending cast: a hardcoded list would go stale
  // and, on a product that sells provenance, would be quietly dishonest.
  const [entities, setEntities] = useState<string[]>([]);
  const box = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Focus without the browser's scroll-into-view: autoFocus slid the query
    // and the masthead under the sticky header on load.
    box.current?.focus({ preventScroll: true });
    setPrimaryLang(loadProfile()?.languages?.[0] ?? "en");
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
      // Clearing the box mid-flight used to strand `loading` at true: the
      // cleanup cancels, and the in-flight finally is guarded by !cancelled.
      setLoading(false);
      return;
    }
    setLoading(true);
    setFailed(false);
    // clearTimeout cancels the timer, not an in-flight request: without the
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
        // A network failure REJECTS (searchEvents only swallows !res.ok).
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

  const term = q.trim();
  useScrollRestore(`search:${term}:scrollY`, resultsTerm === term && results.length > 0);

  // The strip filters what came back; the API searches everything.
  const shown = useMemo(() => {
    const g = sectorGroup(group);
    const rows = g ? results.filter((r) => g.sectors.includes(r.sector ?? "")) : results;
    return chartOrder(rows);
  }, [results, group]);

  const count = searched && !loading && !failed ? `${shown.length} ${shown.length === 1 ? "result" : "results"}` : null;
  const outlets = new Set(shown.flatMap((i) => (i.outlets ?? []).map((o) => o.publisher)));
  const strip = count ? `${count}${outlets.size ? ` · ${outlets.size} ${outlets.size === 1 ? "outlet" : "outlets"}` : ""}` : null;

  return (
    <div className="mx-auto max-w-[var(--shell)] px-[var(--gutter)] pb-[calc(var(--tabbar)+24px)] lg:pb-12">
      <Masthead dateline="Search" />
      <div className="lg:grid lg:grid-cols-[var(--rail)_minmax(0,1fr)] lg:gap-8 lg:pt-6">
        <SectorStrip active={group} onPick={setGroup} allHref="/search" allLabel="All stories" responsiveRail />
        <div className="grid min-w-0 content-start gap-2.5 pt-4 lg:pt-0">
          {/* Design System v2 · TextField, type=search, with its Clear button. */}
          <div className="relative">
            <input
              ref={box}
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Escape" && setQ("")}
              placeholder="Search stories, people, places"
              aria-label="Search stories, entities and sources"
              className={`p-input [&::-webkit-search-cancel-button]:appearance-none ${q ? "pr-20" : ""}`}
            />
            {q && (
              <div className="absolute inset-y-0.5 right-1.5 flex items-center">
                <button type="button" onClick={() => setQ("")} className="p-btn p-btn--ghost p-btn--sm" aria-label="Clear search">Clear</button>
              </div>
            )}
          </div>
          <p className="p-count">{strip ?? "Stories · people · tickers · CVE ids"}</p>

          {term.length < 2 && !loading && entities.length > 0 && (
            <div className="mt-2 grid gap-2.5">
              <p className="p-eyebrow">In the news now</p>
              <div className="flex flex-wrap gap-1.5">
                {entities.map((e) => (
                  <button key={e} type="button" onClick={() => setQ(e)} className="p-chip">{e}</button>
                ))}
              </div>
            </div>
          )}

          <section aria-label="Results" className="pt-1">
            {loading && <p className="p-count py-6">Searching…</p>}
            {!loading && failed && (
              <div className="p-alert p-alert--error" role="status">
                <p>Search is unreachable right now: check your connection and try again.</p>
              </div>
            )}
            {!loading && !failed && searched && results.length === 0 && (
              <EmptyState title={<>Nothing matches &ldquo;{term}&rdquo;</>}>
                Search reads the headline and summary of every record, newest first.
              </EmptyState>
            )}
            {!loading && !failed && searched && results.length > 0 && shown.length === 0 && (
              <EmptyState title={<>None of the {results.length} matches for &ldquo;{term}&rdquo; are in {sectorGroup(group)?.name}.</>} />
            )}
            {shown.length > 0 && (
              <ol className="p-print grid gap-2.5">
                {shown.map((item) => <ChartRow key={item.id} item={item} primaryLang={primaryLang} />)}
              </ol>
            )}
          </section>
        </div>
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
