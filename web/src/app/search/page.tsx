"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChartRow } from "@/components/ChartRow";
import { Masthead } from "@/components/Masthead";
import { SectorStrip } from "@/components/SectorStrip";
import { fetchTrending, searchEvents, type FeedItem } from "@/lib/api";
import { chartOrder } from "@/lib/chart";
import { loadProfile } from "@/lib/profile";
import { sectorGroup } from "@/lib/sectors";
import { useScrollRestore } from "@/lib/useScrollRestore";

/**
 * Search (shape brief §6): the chart with a query field on the masthead's
 * second line. Results are chart rows, most-corroborated first; the sector
 * strip filters them in place. A failed request says so, in its own line —
 * never "no matches" for an error.
 */
const MONO = "font-mono text-[10.5px] uppercase tracking-[0.06em]";
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

  useEffect(() => {
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
  const dateline = count ? `${count}${sources ? ` · ${sources} ${sources === 1 ? "source" : "sources"}` : ""}` : null;

  const chip = (label: string, mono = false) => (
    <button
      key={label}
      onClick={() => setQ(label)}
      className={`${mono ? "font-mono text-[11.5px]" : "text-[13.5px]"} border px-3 py-1.5 transition hover:opacity-70`}
      style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
    >
      {label}
    </button>
  );

  return (
    <div className="mx-auto max-w-[1240px] px-5 pb-24 sm:px-8 lg:pb-16">
      <Masthead dateline={dateline} />
      {/* The query is the masthead's second line: the thing you typed is the headline of this screen. */}
      <input
        autoFocus
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => e.key === "Escape" && setQ("")}
        placeholder="Search"
        aria-label="Search stories, entities and sources"
        className="w-full border-0 bg-transparent p-0 pb-2 text-[26px] font-medium leading-tight outline-none placeholder:opacity-40 sm:text-[32px]"
        style={{ color: "var(--ink)" }}
      />
      <p className={`${MONO} pb-2`} style={{ color: "var(--ink-faint)" }}>
        stories · entities · tickers · CVE ids · Esc clears
      </p>
      <SectorStrip active={group} onPick={setGroup} allLabel="All" />

      {term.length < 2 && !loading && (
        <div className="grid gap-8 pt-6 lg:grid-cols-2 lg:gap-14">
          <div>
            <p className={MONO} style={{ color: "var(--ink-faint)" }}>Trending entities</p>
            <div className="mt-3 flex flex-wrap gap-2">{entities.map((e) => chip(e))}</div>
          </div>
          <div>
            <p className={MONO} style={{ color: "var(--ink-faint)" }}>Try</p>
            <div className="mt-3 flex flex-wrap gap-2">{TRY.map((t) => chip(t, true))}</div>
          </div>
        </div>
      )}

      <section aria-label="Results" className="pt-3">
        {loading && (
          <p className={`${MONO} rule-live py-6`} style={{ color: "var(--ink-faint)" }}>Searching…</p>
        )}
        {!loading && failed && (
          <p className="rule-live py-6 text-[14.5px]" style={{ color: "var(--danger)" }} role="status">
            Search is unreachable right now: check your connection and try again.
          </p>
        )}
        {!loading && !failed && searched && results.length === 0 && (
          <p className="rule-live py-6 text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
            No stories match &ldquo;{term}&rdquo;.
          </p>
        )}
        {!loading && !failed && searched && results.length > 0 && shown.length === 0 && (
          <p className="rule-live py-6 text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
            None of the {results.length} matches for &ldquo;{term}&rdquo; are in {sectorGroup(group)?.name}.
          </p>
        )}
        {shown.length > 0 && (
          <ol className="chart-print">
            {shown.map((item) => <ChartRow key={item.id} item={item} primaryLang={primaryLang} />)}
          </ol>
        )}
      </section>
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
