"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChartRow } from "@/components/ChartRow";
import { Masthead } from "@/components/Masthead";
import { SectorStrip } from "@/components/SectorStrip";
import { SearchIcon } from "@/components/icons";
import { fetchTrending, searchEvents, type FeedItem } from "@/lib/api";
import { chartOrder } from "@/lib/chart";
import { loadProfile } from "@/lib/profile";
import { sectorGroup } from "@/lib/sectors";
import { useScrollRestore } from "@/lib/useScrollRestore";

/**
 * Search: the query field first, then results on the story row grammar,
 * most-corroborated first; the subject nav filters them in place. A failed
 * request says so, in its own line — never "no matches" for an error.
 */
const LABEL = "text-[12.5px] font-semibold uppercase tracking-[0.06em]";
const HINT = "font-mono text-[12px] tracking-[0.02em]";
const TRY = ["RELIANCE", "CVE-2026-62144", "Kerala"];

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
  const sources = shown.reduce((n, i) => n + (i.source_count || 0), 0);
  const outlets = new Set(shown.flatMap((i) => (i.outlets ?? []).map((o) => o.publisher)));
  const dateline = count ? `${count}${outlets.size ? ` · ${outlets.size} ${outlets.size === 1 ? "outlet" : "outlets"}` : ""}` : null;

  const chip = (label: string, mono = false) => (
    <button key={label} onClick={() => setQ(label)} className={`chip ${mono ? "font-mono text-[12px]" : ""}`}>
      {label}
    </button>
  );

  return (
    <div className="mx-auto max-w-[var(--shell)] px-5 pb-[calc(var(--tabbar)+24px)] sm:px-8 lg:pb-16 xl:px-10">
      <Masthead dateline={null} />
      <div className="lg:grid lg:grid-cols-[var(--rail)_minmax(0,1fr)] lg:gap-10 lg:pt-6">
        <SectorStrip active={group} onPick={setGroup} allHref="/search" allLabel="All stories" responsiveRail />
        <div className="min-w-0">
          {/* The query is the headline of this screen: a large field, its own row. */}
          <label className="mt-2 flex h-14 items-center gap-3 rounded-full border px-5 lg:mt-0" style={{ borderColor: "var(--line-strong)", background: "var(--surface)" }}>
            <SearchIcon size={20} className="shrink-0" />
            <input
              ref={box}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Escape" && setQ("")}
              placeholder="Search stories, people, places"
              aria-label="Search stories, entities and sources"
              className="w-full bg-transparent text-[18px] font-medium outline-none placeholder:font-normal placeholder:text-[var(--ink-3)]"
              style={{ color: "var(--ink)" }}
            />
            {q && (
              <button type="button" onClick={() => setQ("")} className="btn btn-ghost btn-sm -mr-2" aria-label="Clear search">Clear</button>
            )}
          </label>
          <p className={`${HINT} mt-2 pb-2`} style={{ color: "var(--ink-3)" }}>
            {dateline ?? <>Stories · people · tickers · CVE ids</>}
          </p>
          {term.length < 2 && !loading && (
            <div className="grid gap-8 pt-4 lg:grid-cols-2 lg:gap-14">
              <div>
                <p className={LABEL} style={{ color: "var(--ink-3)" }}>In the news now</p>
                <div className="mt-3 flex flex-wrap gap-2">{entities.map((e) => chip(e))}</div>
              </div>
              <div>
                <p className={LABEL} style={{ color: "var(--ink-3)" }}>Try</p>
                <div className="mt-3 flex flex-wrap gap-2">{TRY.map((t) => chip(t, true))}</div>
              </div>
            </div>
          )}

          <section aria-label="Results" className="pt-3">
            {loading && (
              <p className={`${HINT} py-6`} style={{ color: "var(--ink-3)" }}>Searching…</p>
            )}
            {!loading && failed && (
              <div className="card" role="status">
                <p className="text-[14.5px] font-medium" style={{ color: "var(--danger)" }}>Search is unreachable right now: check your connection and try again.</p>
              </div>
            )}
            {!loading && !failed && searched && results.length === 0 && (
              <div className="card py-8 text-center"><p className="text-[15px]" style={{ color: "var(--ink-2)" }}>No stories match &ldquo;{term}&rdquo;.</p></div>
            )}
            {!loading && !failed && searched && results.length > 0 && shown.length === 0 && (
              <div className="card py-8 text-center"><p className="text-[15px]" style={{ color: "var(--ink-2)" }}>None of the {results.length} matches for &ldquo;{term}&rdquo; are in {sectorGroup(group)?.name}.</p></div>
            )}
            {shown.length > 0 && (
              <ol className="chart-print flex flex-col gap-3">
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
