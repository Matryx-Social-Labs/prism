"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Chart } from "@/components/Chart";
import { CoverageBar, CoverageLegend } from "@/components/Coverage";
import { Masthead } from "@/components/Masthead";
import { SectionHead } from "@/components/SectionHead";
import { SectorStrip } from "@/components/SectorStrip";
import { StatusPill } from "@/components/StatusPill";
import { fetchFeed, fetchTrending, type FeedItem, type TrendingStory } from "@/lib/api";
import { staleSince } from "@/lib/staleness";
import { istTime, relativeTime, shortDate } from "@/lib/dateline";
import { loadProfile, type Profile } from "@/lib/profile";
import { loadScope, saveScope, type Scope } from "@/lib/scope";
import { markReturning } from "@/lib/returning";
import { sectorGroup, sectorParam } from "@/lib/sectors";
import { useStateName } from "@/lib/useStateName";

/**
 * Today: the day's records, the same list for everyone (D2). FOR YOU appears
 * once the reader has interests and is the only tab that sends them. Scope
 * (All / your state / National) is a client-side filter on rows the API already
 * tagged, so ALL is identical for every reader.
 *
 * A subject chip re-sorts the list in place; the URL follows (/sector/<slug>).
 * Desktop uses its width for simultaneity: the subject rail on the left, the
 * developing stories and the legend on the right — never longer lines.
 */
type Tab = "today" | "foryou";
const WINDOW = 60;

export function FrontPage({ sector = null }: { sector?: string | null }) {
  const group = sectorGroup(sector);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [ready, setReady] = useState(false);
  const [scope, setScope] = useState<Scope>("all");
  const [tab, setTab] = useState<Tab>("today");
  const [items, setItems] = useState<FeedItem[] | null>(null);
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
    setError(null);
    let cancelled = false;
    fetchFeed({
      sector: group ? sectorParam(group) : undefined,
      interests: tab === "foryou" && hasInterests ? profile?.interests : undefined,
      state: profile?.state ?? undefined,
      scope: profile?.state ? scope : "all",
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

  // The scope is a server-side slice (see /feed `scope`); the page IS the slice.
  const scoped = useMemo(() => items ?? [], [items]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: scoped.length };
    for (const i of scoped) {
      const g = sectorGroup(i.sector);
      if (g) c[g.slug] = (c[g.slug] ?? 0) + 1;
    }
    return c;
  }, [scoped]);

  const dateline = useMemo(() => {
    const d = new Date();
    const day = d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", timeZone: "Asia/Kolkata" });
    if (!items) return day;
    const quiet = staleSince(items);
    return quiet ? `${day} · quiet since ${shortDate(quiet)} ${istTime(quiet)}` : day;
  }, [items]);

  const subline = useMemo(() => {
    if (!items) return null;
    const n = scoped.length >= WINDOW ? `${WINDOW}+` : String(scoped.length);
    const outlets = new Set(scoped.flatMap((i) => (i.outlets ?? []).map((o) => o.publisher)));
    const parts = [`${n} ${scoped.length === 1 ? "record" : "records"}`];
    if (outlets.size) parts.push(`${outlets.size} outlets`);
    parts.push("newest reporting first");
    return parts.join(" · ");
  }, [items, scoped]);

  const primaryLang = profile?.languages?.[0] ?? "en";
  const emptyLabel = group
    ? `No ${group.name} records today`
    : scope === "national" && profile?.state
      ? "No India-wide records yet today"
      : scope === "region" && profile?.state
        ? `Nothing from ${stateName ?? "your state"} yet today`
        : "Nothing on today's record yet";
  const scopes: [Scope, string][] = [["all", "All"], ["region", stateName ?? "Your state"], ["national", "National"]];
  const pick = (s: Scope) => { setScope(s); saveScope(s); };

  return (
    <div className="mx-auto max-w-[var(--shell)] px-5 pb-[calc(var(--tabbar)+24px)] sm:px-8 lg:pb-16 xl:px-10">
      <Masthead dateline={dateline} />
      <div className="lg:grid lg:grid-cols-[var(--rail)_minmax(0,1fr)] lg:gap-10 lg:pt-6 xl:grid-cols-[var(--rail)_minmax(0,1fr)_300px]">
        <SectorStrip active={group?.slug ?? null} responsiveRail counts={counts} />

        <div className="min-w-0">
          {profile?.state && (
            <div className="flex gap-2 pt-2 lg:pt-0" role="group" aria-label="Scope">
              {scopes.map(([s, l]) => (
                <button key={s} onClick={() => pick(s)} aria-pressed={scope === s} className="chip h-8 px-3 text-[13px]">
                  {l}
                </button>
              ))}
            </div>
          )}
          <SectionHead
            id="chart-title"
            title={group ? group.name : tab === "foryou" ? "For you" : "Today"}
            hint={subline ?? undefined}
            right={
              hasInterests && !group ? (
                <div role="tablist" className="seg">
                  {(["today", "foryou"] as Tab[]).map((t) => (
                    <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}>
                      {t === "today" ? "Today" : "For you"}
                    </button>
                  ))}
                </div>
              ) : undefined
            }
          />
          <section aria-labelledby="chart-title">
            {error ? (
              <div className="card" role="status">
                <p className="text-[15px] font-medium" style={{ color: "var(--danger)" }}>Today&rsquo;s record could not load.</p>
                <p className="mt-1 text-[14px]" style={{ color: "var(--ink-2)" }}>{error}</p>
              </div>
            ) : items === null ? (
              <div className="flex flex-col gap-3" aria-busy="true" aria-label="Loading today's record">
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className="row-card px-4 py-4" aria-hidden>
                    <span className="pulse-skel block h-2.5 w-24 rounded" style={{ background: "var(--sunken)" }} />
                    <span className="pulse-skel mt-3 block h-4 rounded" style={{ background: "var(--sunken)", width: ["82%", "68%", "74%", "57%"][i] }} />
                    <span className="pulse-skel mt-2 block h-3 w-[90%] rounded" style={{ background: "var(--sunken)" }} />
                    <span className="pulse-skel mt-4 block h-1.5 w-20 rounded" style={{ background: "var(--sunken)" }} />
                  </div>
                ))}
              </div>
            ) : (
              <Chart items={scoped} primaryLang={primaryLang} pageCode={group?.code ?? null} emptyLabel={emptyLabel} />
            )}
          </section>
        </div>

        <aside className="hidden xl:sticky xl:top-[calc(var(--topbar)+24px)] xl:flex xl:flex-col xl:gap-4 xl:self-start">
          {developing.length > 0 && (
            <div className="card">
              <h3 className="card-h">Developing over days</h3>
              <ol className="flex flex-col gap-3.5">
                {developing.map((s) => (
                  <li key={s.slug}>
                    <Link href={`/trending/${s.slug}`} className="group block">
                      <p className="font-record text-[15.5px] font-medium leading-[1.35] group-hover:underline underline-offset-4">
                        {s.hero_title ?? s.label}
                      </p>
                      <p className="mt-1.5 flex items-center gap-2 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
                        <CoverageBar outlets={[]} fallbackCount={s.source_count} width={56} />
                        {s.developments} developments · {s.source_count} outlets
                        {s.last_updated_at && <> · {relativeTime(s.last_updated_at)}</>}
                      </p>
                    </Link>
                  </li>
                ))}
              </ol>
              <Link href="/trending" className="mt-3 inline-block text-[13.5px] font-semibold hover:underline underline-offset-4" style={{ color: "var(--accent)" }}>
                All developing stories →
              </Link>
            </div>
          )}
          <div className="card">
            <h3 className="card-h">How to read a record</h3>
            <div className="flex flex-col gap-3 text-[13.5px]" style={{ color: "var(--ink-2)" }}>
              <p className="flex items-center gap-2.5">
                <CoverageBar outlets={[{ slug: "a", publisher: "a", name: "", code: "", origin: "national", language: "en" }, { slug: "b", publisher: "b", name: "", code: "", origin: "intl", language: "en" }, { slug: "c", publisher: "c", name: "", code: "", origin: "regional", language: "hi" }]} width={56} />
                Coverage bar — who reported it
              </p>
              <CoverageLegend
                withCounts={false}
                outlets={[{ slug: "a", publisher: "a", name: "", code: "", origin: "national", language: "en" }, { slug: "b", publisher: "b", name: "", code: "", origin: "intl", language: "en" }, { slug: "c", publisher: "c", name: "", code: "", origin: "regional", language: "hi" }]}
              />
              <p className="flex flex-wrap items-center gap-2">
                <StatusPill status="verified" label="Verified" />
                <StatusPill status="provisional" label="Provisional" />
              </p>
              <p>A dashed row has one source so far.</p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
