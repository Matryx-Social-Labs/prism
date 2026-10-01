"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { SectionHead } from "@/components/SectionHead";
import { ChartRow } from "@/components/ChartRow";
import { Masthead } from "@/components/Masthead";
import { SectorStrip } from "@/components/SectorStrip";
import { StatusPill } from "@/components/StatusPill";
import { StoryTimeline } from "@/components/StoryTimeline";
import { Alert, EmptyState, TextField } from "@/components/ui";
import { fetchTrending, searchEvents, type FeedItem, type SearchStory } from "@/lib/api";
import { istTime, shortDate } from "@/lib/dateline";
import { followRel } from "@/lib/seo";
import { loadProfile } from "@/lib/profile";
import { navItem, underNav } from "@/lib/sectors";
import { useScrollRestore } from "@/lib/useScrollRestore";

/**
 * Search (Design System v2 · Reading board, flow 04): the query field first;
 * before typing, one line on what is searched and the names in the news now
 * (real names off the live stories — nothing when that list is empty, never a
 * canned query); then "Records", counted, on the story row grammar, in the
 * API's order, which the subject chips filter in place; a query
 * with nothing behind it says so. The board draws a "People and organisations"
 * section first: /api/v1/search returns records only, so it is not drawn. A
 * failed request says so, in its own line — never "no matches" for an error.
 *
 * Two or more matches in one story collapse under it, in the place of its best
 * match: the story's name, "k of n records", and the matches by day in the
 * order they were first reported. "pilot" listed 20 sibling records of one
 * story before this (2026-10-01).
 */
const FIELD_ID = "search-q";
/** What is searched, on the start screen: the API matches headline, summary and cast. */
const START = "Search every record by its headline, its summary and the people and organisations it names: a story, a person, a place, a ticker or a CVE id.";
/** The API's page (api/routes/search.py, limit 30): a full page may hide more, so it prints "30+". */
const SEARCH_CAP = 30;

type Block = { item: FeedItem; story?: undefined } | { story: SearchStory; items: FeedItem[]; item?: undefined };

/** The results in the API's order, a story group standing where its best match
 *  stood. The subject strip can hide matches: a group left with one is a row again. */
function searchBlocks(shown: FeedItem[], stories: SearchStory[]): Block[] {
  const byId = new Map(shown.map((i) => [i.id, i]));
  const groupOf = new Map<string, { story: SearchStory; items: FeedItem[] }>();
  for (const story of stories) {
    const items = story.event_ids.map((id) => byId.get(id)).filter((i): i is FeedItem => Boolean(i));
    if (items.length < 2) continue;
    for (const i of items) groupOf.set(i.id, { story, items });
  }
  const placed = new Set<string>();
  const out: Block[] = [];
  for (const item of shown) {
    const g = groupOf.get(item.id);
    if (!g) out.push({ item });
    else if (!placed.has(g.story.slug)) {
      placed.add(g.story.slug);
      out.push(g);
    }
  }
  return out;
}

function StoryGroup({ story, items }: { story: SearchStory; items: FeedItem[] }) {
  const verified = story.boundary_status === "verified";
  const unit = verified ? "developments" : "records";
  const latest = story.latest_published_at;
  const developments = items.map((i) => ({
    id: i.id, title: i.title, sector: i.sector, occurred_at: null, first_published_at: i.first_published_at ?? null,
    image_url: null, is_current: false, why: null, source_count: i.source_count,
  }));
  return (
    <li className="grid gap-2 border px-4 pb-1 pt-3.5" style={{ borderStyle: verified ? "solid" : "dashed", borderColor: "var(--line-strong)", borderRadius: "var(--r-record)" }}>
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill status={verified ? "verified" : "provisional"} label={verified ? "Verified" : undefined} />
        <span className="p-meta">
          <span className="p-meta__prov">{items.length} of {story.developments} {unit}</span>
          {latest && <><span className="p-meta__sep" /><span className="p-meta__prov">latest {shortDate(latest)} {istTime(latest)}</span></>}
        </span>
      </div>
      <h2 className="text-balance" style={{ font: "var(--t-title)" }}>
        <Link href={`/trending/${story.slug}`} rel={followRel(verified)} className="underline-offset-4 hover:underline" style={{ color: "var(--ink)" }}>
          {story.label}
        </Link>
      </h2>
      <StoryTimeline story={{ developments, cast: [] }} mode="related" />
    </li>
  );
}

function SearchInner() {
  const params = useSearchParams();
  const router = useRouter();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [results, setResults] = useState<FeedItem[]>([]);
  const [stories, setStories] = useState<SearchStory[]>([]);
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
    // Focus without the browser's scroll-into-view: autoFocus slid the query
    // and the masthead under the sticky header on load.
    document.getElementById(FIELD_ID)?.focus({ preventScroll: true });
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
        const found = await searchEvents(term);
        if (cancelled) return;
        setResults(found.items);
        setStories(found.stories);
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

  // The strip filters what came back; the API searches everything. The API's
  // order stands: re-sorted most-outlets-first, the exact record for a query
  // sank below broad stories that merely mention it (audit 2026-09-27).
  const shown = useMemo(() => results.filter((r) => underNav(group, r)), [results, group]);
  const blocks = useMemo(() => searchBlocks(shown, stories), [shown, stories]);

  const more = !group && results.length >= SEARCH_CAP ? "+" : "";
  const count = searched && !loading && !failed ? `${shown.length}${more} ${shown.length === 1 && !more ? "result" : "results"}` : null;
  const outlets = new Set(shown.flatMap((i) => (i.outlets ?? []).map((o) => o.publisher)));
  const strip = count ? `${count}${outlets.size ? ` · ${outlets.size} ${outlets.size === 1 ? "outlet" : "outlets"}` : ""}` : null;

  return (
    <div className="mx-auto max-w-[720px] px-[var(--gutter)] pb-[calc(var(--tabbar)+24px)] lg:pb-12">
      <Masthead dateline="Search" />
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4 pt-4 lg:pt-8">
        {/* A text field in the searchbox role, so the browser adds no second clear control beside Clear. */}
        <TextField
          id={FIELD_ID}
          type="text"
          role="searchbox"
          inputMode="search"
          enterKeyHint="search"
          autoComplete="off"
          label="Search the record"
          value={q}
          onChange={setQ}
          onKeyDown={(e) => e.key === "Escape" && setQ("")}
          placeholder="A story, a person, a place"
          trailing={q ? <button type="button" onClick={() => setQ("")} className="p-btn p-btn--ghost p-btn--sm" aria-label="Clear search">Clear</button> : undefined}
        />

        {term.length < 2 && !loading && (
          <div className="grid gap-3">
            <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>{START}</p>
            {entities.length > 0 && (
              <div className="grid gap-2.5">
                <p className="p-eyebrow">In the news now</p>
                <div className="flex flex-wrap gap-1.5">
                  {entities.map((e) => (
                    <button key={e} type="button" onClick={() => setQ(e)} className="p-chip">{e}</button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <section aria-label="Results" className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3">
          {loading && <p className="p-count py-6" role="status">Searching…</p>}
          {!loading && failed && (
            <Alert tone="error">Search is unreachable right now: check your connection and try again.</Alert>
          )}
          {!loading && !failed && searched && results.length === 0 && (
            <EmptyState title={<>No records match &ldquo;{term}&rdquo;</>}>
              Search reads every record&rsquo;s headline, summary and the names in it. Try fewer words or a name.
            </EmptyState>
          )}
          {!loading && !failed && searched && results.length > 0 && (
            <>
              <SectionHead id="records-title" title="Records" sub={strip ?? undefined} />
              <SectorStrip active={group} onPick={setGroup} allHref="/search" allLabel="All stories" />
              {shown.length === 0 && (
                <EmptyState title={<>None of the {results.length} matches for &ldquo;{term}&rdquo; are in {navItem(group)?.name}.</>} />
              )}
            </>
          )}
          {shown.length > 0 && (
            <ol className="p-print grid gap-2.5">
              {blocks.map((b) =>
                b.story ? <StoryGroup key={`story-${b.story.slug}`} story={b.story} items={b.items} /> : <ChartRow key={b.item.id} item={b.item} primaryLang={primaryLang} />,
              )}
            </ol>
          )}
        </section>
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
