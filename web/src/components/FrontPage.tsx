"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Chart } from "@/components/Chart";
import { Masthead } from "@/components/Masthead";
import { SectorStrip } from "@/components/SectorStrip";
import { fetchFeed, type FeedItem } from "@/lib/api";
import { istDate } from "@/lib/dateline";
import { loadProfile, type Profile } from "@/lib/profile";
import { loadScope, saveScope, type Scope } from "@/lib/scope";
import { markReturning } from "@/lib/returning";
import { sectorGroup, sectorParam } from "@/lib/sectors";

/**
 * The front page: today's chart.
 *
 * TODAY is the same list for everyone — no interests are sent, so a founder, a
 * reviewer and a stranger can point at the same row (D2). FOR YOU appears only
 * once the reader has told us what they follow, and is the only tab that sends
 * interests. Scope (All / your state / National) is a client-side filter on the
 * rows the API already tagged, so ALL is identical for every reader.
 *
 * A sector code re-sorts the chart in place: the same day's rows, filtered,
 * none of the chrome moving. The URL follows (/sector/<slug>) so it can be shared.
 */
type Tab = "today" | "foryou";
const PROMISE_SEEN = "prism.promise.seen";
const WINDOW = 60;

export function FrontPage({ sector = null }: { sector?: string | null }) {
  const group = sectorGroup(sector);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [ready, setReady] = useState(false);
  const [scope, setScope] = useState<Scope>("all");
  const [tab, setTab] = useState<Tab>("today");
  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPromise, setShowPromise] = useState(false);

  useEffect(() => {
    markReturning();
    const p = loadProfile();
    setProfile(p);
    setScope(loadScope(Boolean(p?.state)) ?? "all");
    try {
      if (!p && !window.sessionStorage.getItem(PROMISE_SEEN)) {
        setShowPromise(true);
        window.sessionStorage.setItem(PROMISE_SEEN, "1");
      }
    } catch { /* ignore */ }
    setReady(true);
  }, []);

  const hasInterests = Boolean(profile?.interests?.length);

  useEffect(() => {
    if (!ready) return;
    setError(null);
    let cancelled = false;
    fetchFeed({
      sector: group ? sectorParam(group) : undefined,
      interests: tab === "foryou" && hasInterests ? profile?.interests : undefined,
      state: profile?.state ?? undefined,
      languages: profile?.languages,
      sort: "latest",
      limit: WINDOW,
    })
      .then((list) => { if (!cancelled) setItems(list); })
      .catch(() => { if (!cancelled) setError("The Prism API is unreachable right now."); });
    return () => { cancelled = true; };
  }, [ready, tab, hasInterests, profile, group]);

  const scoped = useMemo(() => {
    if (!items || scope === "all" || !profile?.state) return items ?? [];
    return items.filter((i) => (scope === "region" ? i.is_regional : !i.is_regional));
  }, [items, scope, profile]);

  // The feed is a window (60), not the day: at the cap say "60+" rather than
  // print the cap as a count; and count the sources behind the rows shown.
  const dateline = useMemo(() => {
    const d = istDate(new Date());
    if (!items) return d;
    const n = scoped.length >= WINDOW ? `${WINDOW}+` : String(scoped.length);
    const sources = scoped.reduce((t, i) => t + (i.source_count || 0), 0);
    return `${d} · ${n} ${scoped.length === 1 ? "story" : "stories"} · ${sources.toLocaleString("en-IN")} ${sources === 1 ? "source" : "sources"}`;
  }, [items, scoped]);

  const primaryLang = profile?.languages?.[0] ?? "en";
  const subject = group ? group.name : "today";
  const emptyLabel = group
    ? `No ${group.name} stories on today's chart`
    : "Nothing on today's chart yet";

  const scopes: [Scope, string][] = [["all", "All"], ["region", "Your state"], ["national", "National"]];
  const pick = (s: Scope) => { setScope(s); saveScope(s); };

  return (
    <div className="mx-auto max-w-[1240px] px-5 pb-24 sm:px-8 lg:pb-20">
      <Masthead dateline={dateline} right={profile?.state ? (
        <div className="flex gap-3 font-mono text-[11px] uppercase tracking-[0.06em]">
          {scopes.map(([s, l]) => (
            <button key={s} onClick={() => pick(s)} aria-pressed={scope === s}
              className="underline-offset-4 aria-pressed:underline"
              style={{ color: scope === s ? "var(--ink)" : "var(--ink-faint)" }}>{l}</button>
          ))}
        </div>
      ) : null} />
      <SectorStrip active={group?.slug ?? null} />
      <h1 id="chart-title" className="pt-4 font-display text-[26px] uppercase leading-none tracking-[0.03em]">
        {group ? group.name : tab === "foryou" ? "For you" : "Today"}
      </h1>
      {showPromise && !group && (
        <p className="rule-live py-3 text-[14px]" style={{ color: "var(--ink-muted)" }}>
          One story. Every perspective.{" "}
          <Link href="/about" className="underline underline-offset-4" style={{ color: "var(--ink)" }}>
            How Prism reads a story&nbsp;→
          </Link>
        </p>
      )}
      {hasInterests && !group && (
        <div role="tablist" className="flex gap-5 pt-4 font-display text-[18px] uppercase tracking-[0.04em]">
          {(["today", "foryou"] as Tab[]).map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
              className="border-b-2 pb-1"
              style={{ borderColor: tab === t ? "var(--ink)" : "transparent", color: tab === t ? "var(--ink)" : "var(--ink-faint)" }}>
              {t === "today" ? "Today" : "For you"}
            </button>
          ))}
        </div>
      )}
      <section aria-labelledby="chart-title" className="pt-3">
        {error ? (
          <p className="rule-live py-6 text-[14.5px]" style={{ color: "var(--danger)" }}>{error}</p>
        ) : items === null ? (
          <p
            className="rule-live py-6 font-mono text-[11px] uppercase tracking-[0.06em]"
            style={{ color: "var(--ink-faint)" }}
            aria-busy="true"
          >
            Printing today&rsquo;s chart…
          </p>
        ) : (
          <Chart items={scoped} primaryLang={primaryLang} emptyLabel={emptyLabel} yesterdayHref="/feed/yesterday" />
        )}
      </section>
    </div>
  );
}
