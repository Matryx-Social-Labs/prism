import type { ReactElement } from "react";
import { ImageResponse } from "next/og";

import { type EventDetail, fetchArchiveDay, fetchEntity, fetchEvent, fetchSources, fetchStateHub, fetchTrendingStory } from "@/lib/api";
import { dayRevalidate, istToday, longDay, parseDay } from "@/lib/archive";
import { monitoredText } from "@/lib/coverage";
import { SCHEMA_KIND } from "@/lib/entities";
import { langName, languageList } from "@/lib/languages";
import {
  CARD_TEXT, type CardFormat, CollectionCard, type Figure, FORMATS, type PillSpec, QuoteCard, SITE_HEADLINE, SITE_LINE, SiteCard,
  StoryCard, stamp, tally,
} from "@/lib/ogCard";
import { ogFonts } from "@/lib/ogFonts";
import { findQuote } from "@/lib/quotes";
import { stateBySlug } from "@/lib/regions";
import { sectorGroup } from "@/lib/sectors";
import { indexSources } from "@/lib/sources";
import { spanDays } from "@/lib/spine";

// Every share card, built once for any shape: the link preview (each route's
// opengraph-image) and Instagram's post and Story (/card/<format>/<path>, for
// the founders' Marketing page). A builder returns the card and the words it
// draws (for the font subset), or null when its page cannot be read, and then
// the brand card is served uncached, never a stand-in. No LLM, Node runtime.

type Built = { el: ReactElement; text: string[] } | null;

/** The pill the story page prints: one source so far, or the arc's boundary once its owner says (StoryView). */
async function statusOf(e: EventDetail, single: boolean): Promise<PillSpec | null> {
  if (single) return { label: "One source so far", dashed: true };
  const arc = e.story_slug ? await fetchTrendingStory(e.story_slug).catch(() => null) : null;
  if (!arc) return null;
  return arc.boundary_status === "verified" ? { label: "Verified record", check: true } : { label: "Provisional grouping", dashed: true };
}

/** A record (share cards v3): its status, the mono meta line, the headline at poster scale, the counted bar. */
export async function storyCard(id: string, format: CardFormat): Promise<Built> {
  const e = await fetchEvent(id);
  const t = tally(e.sources.map((s) => ({ publisher: s.publisher ?? s.source_name, origin: s.origin, language: s.language })));
  const single = e.sources.length === 1;
  const pill = await statusOf(e, single);
  // The news's own clock (lib/dateline newsTime): the newest report, not the projection rebuild.
  const newest = e.sources.map((s) => s.published_at).filter((x): x is string => !!x).sort().at(-1) ?? e.last_updated_at;
  // One language is named here; several are counted on the count line, so the
  // mono line never wraps and orphans a code ("· ML") on a multi-language record.
  const meta = [sectorGroup(e.sector)?.name ?? "", single ? stamp(newest) : `Updated ${stamp(newest)}`, ...(t.languages.length === 1 ? [t.languages[0].toUpperCase()] : [])];
  // Out of the monitored set, as the record's header prints it: the record's
  // own denominator, or the public list's for an older payload.
  const monitored = e.monitored_outlets ?? (await fetchSources())?.outlets ?? null;
  const counted = single
    ? `${monitoredText(1, monitored)} · the record grows as others report`
    : `${monitoredText(t.outlets, monitored)}${t.languages.length > 1 ? ` · ${t.languages.length} languages` : ""}`;
  const path = `/story/${id}`;
  return {
    el: <StoryCard path={path} pill={pill} meta={meta} headline={e.title} tally={t} count={counted} single={single} format={format} />,
    text: [e.title, ...meta, counted, path],
  };
}

/**
 * A trending group: its status, subject and span, its headline, and — for a
 * VERIFIED arc only — the route of its developments; a provisional group is
 * related coverage, never a chronology (PRODUCT.md), so it gets no route.
 */
export async function trendingCard(slug: string, format: CardFormat): Promise<Built> {
  const [s, set] = await Promise.all([fetchTrendingStory(slug).catch(() => null), fetchSources()]);
  if (!s) return null;
  const verified = s.boundary_status === "verified";
  const t = tally((s.outlets ?? []).map((o) => o.outlet));
  const devs = s.developments.length;
  const days = spanDays(s.developments);
  const dated = s.developments.map((d) => d.occurred_at).filter((x): x is string => !!x);
  const route = verified && dated.length === devs ? dated.sort() : null;
  const meta = [sectorGroup(s.sector)?.name ?? "", days ? `${days} ${days === 1 ? "day" : "days"}` : ""];
  const unit = verified ? (devs === 1 ? "development" : "developments") : devs === 1 ? "record" : "records";
  const counted = `${devs} ${unit} · ${monitoredText(t.outlets, set?.outlets)}`;
  const path = `/trending/${slug}`;
  return {
    el: (
      <StoryCard
        path={path}
        pill={verified ? { label: "Verified", check: true } : { label: "Grouping under review", dashed: true }}
        meta={meta}
        headline={s.label}
        tally={t}
        count={counted}
        route={route}
        format={format}
      />
    ),
    text: [s.label, ...meta, counted, path, route ? "JANFEBMARAPRMAYJUNJULAUGSEPTOCTNOVDEC" : ""],
  };
}

/**
 * The quote card (PLAN-LAUNCH §6): the sentence as the article printed it, who
 * said it, and OUTLET · [n] · DATE · LANGUAGE — the language it was PRINTED in,
 * because the verbatim check is against the article, not the speaker. The
 * language is printed by its English name: Satori does not shape Indic scripts.
 */
export async function quoteCard(id: string, n: string, format: CardFormat): Promise<Built> {
  const e = await fetchEvent(id);
  const q = findQuote(e.claims, n, e.quote_aliases);
  if (!q) return null;
  const cite = indexSources(e.sources).get(q.claim.article_id);
  const meta = [q.claim.source_name, cite ? `[${cite}]` : "", q.claim.published_at ? stamp(q.claim.published_at) : "", q.claim.lang ? langName(q.claim.lang) : ""];
  const path = `/story/${id}/quote/${q.id}`;
  return {
    el: (
      <QuoteCard path={path} quote={q.claim.quote_text} speaker={q.speaker} role={q.role} meta={meta} translated={q.claim.translated ?? false}
        reported={q.claim.speech === "reported"} storyTitle={e.title} format={format} />
    ),
    text: [q.claim.quote_text, q.speaker, q.role ?? "", ...meta, e.title, path],
  };
}

/** A person or organisation: what the page says they are, and its counts as the page prints them. */
export async function entityCard(slug: string, format: CardFormat): Promise<Built> {
  if (stateBySlug(slug)) return stateCard(slug, format); // the actor address 308s to the state's hub
  const page = await fetchEntity(slug);
  if (!page) return null;
  const quotes = page.quote_count ?? 0;
  const reported = page.reported_count ?? 0;
  const figures: Figure[] = [
    { n: page.record_count, label: page.record_count === 1 ? "Prism record" : "Prism records" },
    ...(quotes ? [{ n: quotes, label: quotes === 1 ? "quote, word for word" : "quotes, word for word" }] : []),
    ...(reported ? [{ n: reported, label: reported === 1 ? "reported statement" : "reported statements" }] : []),
  ];
  const meta = [SCHEMA_KIND[page.entity.schema_type] ?? ""];
  const line = page.role ? `As the articles put it: ${page.role}` : null;
  const path = `/entity/${page.entity.slug}`;
  return {
    el: <CollectionCard path={path} meta={meta} title={page.entity.name} line={line} figures={figures} format={format} />,
    text: [page.entity.name, ...meta, line ?? "", ...figures.map((f) => `${f.n} ${f.label}`), path],
  };
}

/** A state's hub: its stories from two or more outlets in the window, all its records, the outlets with a desk there. */
export async function stateCard(slug: string, format: CardFormat): Promise<Built> {
  const hub = stateBySlug(slug);
  if (!hub) return null;
  const s = await fetchStateHub(hub.code);
  if (!s) return null;
  const figures: Figure[] = [
    { n: s.multi_outlet, label: s.multi_outlet === 1 ? "story from two or more outlets" : "stories from two or more outlets" },
    { n: s.records, label: s.records === 1 ? "record, one outlet or more" : "records, one outlet or more" },
    { n: s.desks.length, label: s.desks.length === 1 ? "outlet with a desk here" : "outlets with a desk here" },
  ];
  const meta = [hub.kind, `Last ${s.window_days} days`];
  const line = s.languages.length ? `Reported in ${languageList(s.languages)}` : null;
  const path = `/state/${hub.slug}`;
  return {
    el: <CollectionCard path={path} meta={meta} title={hub.name} line={line} figures={figures} format={format} />,
    text: [hub.name, ...meta, line ?? "", ...figures.map((f) => `${f.n} ${f.label}`), path],
  };
}

/** One IST day's record: its stories from two or more outlets, those from one, its languages; or that Prism was not reading. */
export async function dayCard(date: string, format: CardFormat): Promise<Built> {
  const day = parseDay(date);
  if (!day || day === istToday()) return null;
  const d = await fetchArchiveDay(day, dayRevalidate(day));
  if (!d) return null;
  const figures: Figure[] = d.read
    ? [
        { n: d.multi_outlet ?? 0, label: d.multi_outlet === 1 ? "story from two or more outlets" : "stories from two or more outlets" },
        ...(d.single_source !== null ? [{ n: d.single_source, label: d.single_source === 1 ? "story from one outlet" : "stories from one outlet" }] : []),
        ...(d.languages !== null ? [{ n: d.languages, label: d.languages === 1 ? "language" : "languages" }] : []),
      ]
    : [];
  const line = !d.read
    ? "Prism was not reading on this day, so nothing on it was counted."
    : d.whole_day && d.settled ? null : "Prism read part of this day, so this record is not all of it.";
  const meta = ["The day's record", "IST"];
  const title = longDay(day);
  const path = `/feed/${day}`;
  return {
    el: <CollectionCard path={path} meta={meta} title={title} line={line} figures={figures} format={format} />,
    text: [title, ...meta, line ?? "", ...figures.map((f) => `${f.n} ${f.label}`), path],
  };
}

/** The brand card: the promise and one sentence, on the ink ground. */
export async function siteCard(format: CardFormat): Promise<Built> {
  return { el: <SiteCard headline={SITE_HEADLINE} line={SITE_LINE} format={format} />, text: [SITE_HEADLINE, SITE_LINE] };
}

/** The card a page's path shares, for /card/<format>/<path>: the brand card for a page without its own. */
export function cardForPath(segments: string[], format: CardFormat): Promise<Built> {
  const [first, a, b, c] = segments;
  if (first === "story" && a && !b) return storyCard(a, format);
  if (first === "story" && a && b === "quote" && c) return quoteCard(a, c, format);
  if (first === "trending" && a && !b) return trendingCard(a, format);
  if (first === "entity" && a && !b) return entityCard(a, format);
  if (first === "state" && a && !b) return stateCard(a, format);
  if (first === "feed" && a && !b) return dayCard(a, format);
  return siteCard(format);
}

/**
 * The image for a built card. A card whose page could not be read is the brand
 * card, uncached: a generic card served as a 200 would be kept by the scraper
 * for days. `headers` for the Instagram shapes, which a founder downloads
 * and may download again once the counts move.
 */
export async function cardImage(build: Promise<Built>, format: CardFormat, headers?: Record<string, string>): Promise<ImageResponse> {
  const { width, height } = FORMATS[format];
  const card = await build.catch(() => null);
  if (!card) {
    const fonts = await ogFonts(SITE_HEADLINE, SITE_LINE, CARD_TEXT);
    return new ImageResponse(<SiteCard headline={SITE_HEADLINE} line={SITE_LINE} format={format} />,
      { width, height, fonts: fonts.length ? fonts : undefined, headers: { "cache-control": "no-store" } });
  }
  const fonts = await ogFonts(...card.text, CARD_TEXT);
  return new ImageResponse(card.el, { width, height, fonts: fonts.length ? fonts : undefined, ...(headers ? { headers } : {}) });
}
