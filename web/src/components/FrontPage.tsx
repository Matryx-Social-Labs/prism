"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Chart } from "@/components/Chart";
import { lensMarkers } from "@/components/ChartRow";
import { EmptyState } from "@/components/ui";
import { Masthead } from "@/components/Masthead";
import { SectionHead } from "@/components/SectionHead";
import { SectorStrip } from "@/components/SectorStrip";
import { TodayAside } from "@/components/today/TodayAside";
import { TopOfRecord } from "@/components/today/TopOfRecord";
import { fetchFeed, fetchTrending, type FeedItem, type TrendingStory } from "@/lib/api";
import { chartOrder } from "@/lib/chart";
import { staleSince } from "@/lib/staleness";
import { istTime, shortDate } from "@/lib/dateline";
import { loadProfile, type Profile } from "@/lib/profile";
import { loadScope, saveScope, type Scope } from "@/lib/scope";
import { markReturning } from "@/lib/returning";
import { sectorGroup, sectorParam } from "@/lib/sectors";
import { RowListSkeleton } from "@/components/Skeletons";
import { FEED_WINDOW } from "@/lib/feedWindow";
import { useScrollRestore } from "@/lib/useScrollRestore";
import { useStateName } from "@/lib/useStateName";

/**
 * Today: the day's records, the same list for everyone (D2). FOR YOU appears
 * once the reader has interests and is the only tab that sends them. Scope
 * (All / your state / National) is a client-side filter on rows the API already
 * tagged, so ALL is identical for every reader.
 *
 * A subject chip re-sorts the list in place; the URL follows (/sector/<slug>).
 * Pages v3 · Today: on the phone, the day's multi-outlet stories lead as a card
 * rail (All + Today only). Desktop uses its width for simultaneity: the subject
 * rail on the left, the list in two columns, the developing stories and the
 * legend on the right — never longer lines.
 *
 * "Has a professional read" (adopted in the design 25 Sep) keeps only the rows
 * that earn a lens — the same test that draws their lens mark — and says so
 * when none do.
 *
 * `initial` is the ALL list the server already fetched, so the rows are in the
 * HTML a crawler receives (Google renders JS late; GPTBot, ClaudeBot and
 * PerplexityBot never do — the day's record was invisible to all of them,
 * 2026-09-21). The first client fetch is skipped when the reader's slice IS
 * that default; a state, a language or FOR YOU re-fetches as before.
 */
type Tab = "today" | "foryou";
const WINDOW = FEED_WINDOW;

export function FrontPage({ sector = null, initial = null }: { sector?: string | null; initial?: FeedItem[] | null }) {
  const group = sectorGroup(sector);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [ready, setReady] = useState(false);
  const [scope, setScope] = useState<Scope>("all");
  const [tab, setTab] = useState<Tab>("today");
  const [lensOnly, setLensOnly] = useState(false);
  const [items, setItems] = useState<FeedItem[] | null>(initial);
  const seeded = useRef(initial !== null);
  const [developing, setDeveloping] = useState<TrendingStory[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    markReturning();
    const p = loadProfile();
    setProfile(p);
    setScope(loadScope(Boolean(p?.state)) ?? "all");
    setReady(true);
  }, []);

  const hasInterests = Boolean(profile?.interests?.length);
  const stateName = useStateName(profile?.state ?? null);

  useEffect(() => {
    if (!ready) return;
    if (seeded.current) {
      seeded.current = false;
      const isDefault = !(tab === "foryou" && hasInterests) && !profile?.state && scope === "all" && !profile?.languages?.length;
      if (isDefault) return;
    }
    setError(null);
    let cancelled = false;
    fetchFeed({
      sector: group ? sectorParam(group) : undefined,
      interests: tab === "foryou" && hasInterests ? profile?.interests : undefined,
      state: profile?.state ?? undefined,
      scope: scope === "region" && !profile?.state ? "all" : scope,
      languages: profile?.languages,
      sort: "latest",
      limit: WINDOW,
    })
      .then((list) => { if (!cancelled) setItems(list); })
      .catch(() => { if (!cancelled) setError("The Prism API is unreachable right now."); });
    return () => { cancelled = true; };
  }, [ready, tab, hasInterests, profile, group, scope]);

  // The right rail: stories developing over days — a different cut from the
  // list, not the same rows twice. Best effort; the list never waits for it.
  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    fetchTrending({ state: profile?.state ?? null, limit: 5 })
      .then((s) => { if (!cancelled) setDeveloping(s); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [ready, profile]);

  // Coming back from a story lands where the reader left the chart, not at the
  // top (founder, 2026-09-20). Keyed by the slice, so Karnataka's offset never
  // restores onto National's list. Search and Stories already do this.
  useScrollRestore(`feed:${sector ?? "all"}:${tab}:${scope}:scrollY`, items !== null && items.length > 0);

  // The scope is a server-side slice (see /feed `scope`); the page IS the slice.
  const scoped = useMemo(() => items ?? [], [items]);
  const shown = useMemo(() => (lensOnly ? scoped.filter((i) => lensMarkers(i).length > 0) : scoped), [scoped, lensOnly]);

  const counts = useMemo(() => {
    // On a subject page the list IS that subject, so "All stories" gets no count.
    const c: Record<string, number> = group ? {} : { all: scoped.length };
    for (const i of scoped) {
      const g = sectorGroup(i.sector);
      if (g) c[g.slug] = (c[g.slug] ?? 0) + 1;
    }
    return c;
  }, [scoped, group]);

  const dateline = useMemo(() => {
    const d = new Date();
    const day = d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", timeZone: "Asia/Kolkata" });
    if (!items) return day;
    const quiet = staleSince(items);
    return quiet ? `${day} · quiet since ${shortDate(quiet)} ${istTime(quiet)}` : day;
  }, [items]);

  // The counts under the head and at the end of the list. The list is ordered by
  // chartOrder (most outlets first, ties by recency), so the strip says that.
  const tally = useMemo(() => {
    if (!items) return null;
    // A full window means more exist than were loaded: "24+", and a filtered
    // count says which window it was taken from ("3 of 24+ records").
    const capped = scoped.length >= WINDOW;
    const n = lensOnly ? `${shown.length} of ${capped ? `${WINDOW}+` : scoped.length}` : capped ? `${WINDOW}+` : String(shown.length);
    const outlets = new Set(shown.flatMap((i) => (i.outlets ?? []).map((o) => o.publisher)));
    const parts = [`${n} ${(lensOnly ? scoped.length : shown.length) === 1 ? "record" : "records"}`];
    if (outlets.size) parts.push(`${outlets.size} ${outlets.size === 1 ? "outlet" : "outlets"}`);
    return parts.join(" · ");
  }, [items, scoped, shown, lensOnly]);

  // Top of the record: the most-reported multi-outlet stories, on All + Today only.
  const top = useMemo(() => (group || tab !== "today" ? [] : chartOrder(scoped).filter((i) => i.source_count > 1).slice(0, 5)), [group, tab, scoped]);

  const primaryLang = profile?.languages?.[0] ?? "en";
  const emptyLabel = group
    ? `No ${group.name} records today`
    : scope === "national"
      ? "No India-wide records yet today"
      : scope === "world"
        ? "No world records yet today"
        : scope === "region" && profile?.state
          ? `Nothing from ${stateName ?? "your state"} yet today`
          : "Nothing on today's record yet";
  // The state pill needs a state; All, National and World do not.
  const scopes: [Scope, string][] = [
    ["all", "All"],
    ...(profile?.state ? ([["region", stateName ?? "Your state"]] as [Scope, string][]) : []),
    ["national", "National"],
    ["world", "World"],
  ];
  const pick = (s: Scope) => { setScope(s); saveScope(s); };

  const list = error ? (
    <div className="p-alert p-alert--error" role="status">
      <div>
        <p className="p-alert__title">Today&rsquo;s record could not load.</p>
        <p style={{ color: "var(--ink-2)" }}>{error}</p>
      </div>
    </div>
  ) : items === null ? (
    <RowListSkeleton n={7} label="Loading today's record" />
  ) : lensOnly && shown.length === 0 && scoped.length > 0 ? (
    <EmptyState
      title={`No stories with a professional read ${group ? `in ${group.name} ` : ""}today`}
      action={<button type="button" className="p-btn p-btn--text" onClick={() => setLensOnly(false)}>Show every story</button>}
    />
  ) : (
    <Chart items={shown} primaryLang={primaryLang} pageCode={group?.code ?? null} emptyLabel={emptyLabel} />
  );

  return (
    <div className="mx-auto max-w-[var(--shell)] px-[var(--gutter)] pb-[calc(var(--tabbar)+24px)] lg:pb-12">
      <Masthead dateline={dateline} />
      <div className="lg:grid lg:grid-cols-[var(--rail)_minmax(0,1fr)] lg:gap-8 lg:pt-6 xl:grid-cols-[var(--rail)_minmax(0,1fr)_var(--evidence)]">
        <SectorStrip active={group?.slug ?? null} responsiveRail counts={counts} />

        <div className="min-w-0">
          <TopOfRecord stories={top} />
          <div className="grid gap-3 pt-5 lg:pt-0">
            <SectionHead
              id="chart-title"
              as="h1"
              title={group ? group.name : tab === "foryou" ? "For you" : "Today"}
              sub={tally ? `${tally} · most-reported first` : undefined}
              right={
                hasInterests && !group ? (
                  <div role="tablist" aria-label="Which record" className="p-seg">
                    {(["today", "foryou"] as Tab[]).map((t) => (
                      <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}>
                        {t === "today" ? "Today" : "For you"}
                      </button>
                    ))}
                  </div>
                ) : undefined
              }
            />
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex flex-wrap gap-1.5" role="group" aria-label="Scope">
                {scopes.map(([s, l]) => (
                  <button key={s} onClick={() => pick(s)} aria-pressed={scope === s} className="p-chip min-h-8 px-3 text-[13px]">
                    {l}
                  </button>
                ))}
              </div>
              <button type="button" onClick={() => setLensOnly((v) => !v)} aria-pressed={lensOnly} className="p-chip min-h-8 px-3 text-[13px]">
                <i aria-hidden="true" className="h-2 w-2 rounded-full" style={{ background: lensOnly ? "var(--paper)" : "var(--lens-markets)" }} />
                Has a professional read
              </button>
            </div>
          </div>
          <section aria-labelledby="chart-title" className="pt-2 lg:pt-3.5">
            {list}
          </section>
          {tally && !error && shown.length > 0 && (
            <div className="mt-7 flex flex-wrap items-baseline gap-3 py-5" style={{ borderTop: "var(--rule-section) solid var(--ink)" }}>
              <p style={{ font: "var(--t-title)" }}>That&rsquo;s today&rsquo;s record.</p>
              <span className="p-count">{tally}</span>
            </div>
          )}
        </div>

        <TodayAside developing={developing} />
      </div>
    </div>
  );
}
