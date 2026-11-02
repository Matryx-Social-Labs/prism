"use client";

import Link from "next/link";
import { useState } from "react";
import { ChartRow } from "@/components/ChartRow";
import { CoverageBar, OutletIcon, coverageText } from "@/components/Coverage";
import { PhotoImg } from "@/components/PhotoImg";
import { SectionHead } from "@/components/SectionHead";
import { StatusPill } from "@/components/StatusPill";
import { Ago } from "@/components/Ago";
import type { FeedItem, TrendingStory } from "@/lib/api";
import { REPORT_IMAGES } from "@/lib/images";
import { followRel } from "@/lib/seo";
import type { TodayLayout, TodaySection } from "@/lib/today";

const plural = (n: number, one: string) => `${n} ${one}${n === 1 ? "" : "s"}`;

/** A ranked line beside the lead: number, headline, coverage; the report's photo small at the right. */
function RankedRow({ item, n }: { item: FeedItem; n: number }) {
  const outlets = item.outlets ?? [];
  const photo = REPORT_IMAGES && item.image_url ? item.image_url : null;
  const credit = item.image_outlet ?? null;
  return (
    <li className="border-b" style={{ borderColor: "var(--line)" }}>
      <Link href={`/story/${item.id}`} rel={followRel(item.indexable)} className="group grid grid-cols-[18px_minmax(0,1fr)_auto] items-start gap-3 py-3.5" style={{ color: "var(--ink)" }}>
        <span className="p-count pt-1">{n}</span>
        <span className="grid min-w-0 gap-1.5">
          <span className="underline-offset-4 group-hover:underline" style={{ font: "var(--t-title-s)" }}>{item.title}</span>
          <span className="flex min-w-0 flex-wrap items-center gap-2">
            <CoverageBar outlets={outlets} fallbackCount={item.source_count} width={56} />
            <span className="p-count">{coverageText(outlets, item.source_count)}</span>
          </span>
        </span>
        {photo && (
          <figure className="p-thumb" style={{ width: 88, height: 64 }}>
            <PhotoImg src={photo} alt={credit ? `Photo: ${credit.name}` : "Photo from a report on this story"} />
            {credit && (
              <figcaption className="p-thumb__credit" title={`Photo: ${credit.name}`}>
                <OutletIcon domain={credit.domain} code={credit.code} name={credit.name} size={14} />
              </figcaption>
            )}
          </figure>
        )}
      </Link>
    </li>
  );
}

/** A developing story as a card: its status in words, its own label, its counts. */
function StoryTile({ s }: { s: TrendingStory }) {
  const verified = s.boundary_status === "verified";
  return (
    <li>
      <Link
        href={`/trending/${s.slug}`}
        rel={followRel(verified)}
        className="group grid h-full content-start gap-2.5 border p-3.5"
        style={{ borderColor: "var(--line)", borderRadius: "var(--r-record)", background: "var(--surface)", color: "var(--ink)" }}
      >
        <span className="justify-self-start">
          <StatusPill status={verified ? "verified" : "provisional"} label={verified ? undefined : "Provisional grouping"} />
        </span>
        {/* The story's own name, the one /trending prints: never its lead record's headline. */}
        <span className="underline-offset-4 group-hover:underline" style={{ font: "var(--t-title-s)" }}>{s.label}</span>
        <span className="p-count mt-auto">
          {plural(s.developments, verified ? "development" : "record")} · {plural(s.source_count, "outlet")}
          {s.last_updated_at && <> · <Ago iso={s.last_updated_at} /></>}
        </span>
      </Link>
    </li>
  );
}

/** One section: up to six rows; the rest counted, and reached by its page or opened in place. */
function Section({ s, primaryLang, lastOpened }: { s: TodaySection; primaryLang: string; lastOpened: string | null }) {
  const [open, setOpen] = useState(false);
  const id = `today-${s.key}`;
  const shown = open ? s.all : s.items;
  const more = s.total - s.items.length;
  return (
    <section aria-labelledby={id} className="grid grid-cols-[minmax(0,1fr)] gap-3">
      <SectionHead
        id={id}
        title={s.title}
        count={s.total}
        sub={more > 0 && !open ? `most reported first · ${s.items.length} of ${s.total}` : "most reported first"}
        right={s.href ? <Link href={s.href} className="p-link whitespace-nowrap text-[13.5px]">All {s.title} →</Link> : undefined}
      />
      <ol className="p-print grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {shown.map((it) => (
          <ChartRow key={it.id} item={it} primaryLang={primaryLang} lastOpened={it.id === lastOpened} />
        ))}
      </ol>
      {!s.href && more > 0 && !open && (
        <button type="button" onClick={() => setOpen(true)} className="p-link justify-self-start text-[13.5px]">
          Show the other {more}
        </button>
      )}
    </section>
  );
}

/**
 * Today as one page of sections (2026-11-02), every record once:
 * - the lead beside the next four, ranked (NYT's and Perplexity's lead block);
 * - under the ranked list, the stories developing over days, so the column
 *   beside the lead does not run out halfway down it;
 * - the reader's state, India by subject, then the world (Apple News's sections).
 * The desk spends its width on the lead block and three-column sections instead
 * of side rails that ended after one screen.
 */
export function TodayDesk({ layout, developing, primaryLang, lastOpened }: { layout: TodayLayout; developing: TrendingStory[]; primaryLang: string; lastOpened: string | null }) {
  const { lead, next, sections } = layout;
  if (!lead) return null;
  return (
    <div className="grid gap-10">
      <section aria-labelledby="most-reported" className="grid grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-12 lg:items-start lg:gap-8">
        <ol className="p-print grid lg:col-span-7">
          <ChartRow item={lead} lead draw primaryLang={primaryLang} lastOpened={lead.id === lastOpened} />
        </ol>
        {next.length > 0 && (
          <div className="grid content-start lg:col-span-5">
            <h2 id="most-reported" className="p-eyebrow pb-2" style={{ borderBottom: "var(--rule-section) solid var(--ink)" }}>Most reported today</h2>
            <ol>
              {next.map((it, i) => <RankedRow key={it.id} item={it} n={i + 2} />)}
            </ol>
            {developing.length > 0 && (
              <section aria-labelledby="developing" className="grid gap-2.5 pt-7">
                <h2 id="developing" className="p-eyebrow pb-2" style={{ borderBottom: "var(--rule-section) solid var(--ink)" }}>Developing over days</h2>
                <ol className="grid gap-2.5">
                  {developing.slice(0, 3).map((st) => <StoryTile key={st.slug} s={st} />)}
                </ol>
                <Link href="/trending" className="p-link justify-self-start text-[13.5px]">All developing stories →</Link>
              </section>
            )}
          </div>
        )}
      </section>

      {sections.map((s) => <Section key={s.key} s={s} primaryLang={primaryLang} lastOpened={lastOpened} />)}
    </div>
  );
}
