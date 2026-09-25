import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ChartRow } from "@/components/ChartRow";
import { ArrowUpRight, Check } from "@/components/icons";
import { SectionHead } from "@/components/SectionHead";
import { ShareButton } from "@/components/ShareButton";
import { BackBar } from "@/components/ui";
import { fetchEvent, type EventDetail, type FeedItem, type OutletRef } from "@/lib/api";
import { istTime, shortDate } from "@/lib/dateline";
import { langName, langNative } from "@/lib/languages";
import { quoteLink } from "@/lib/quoteLink";
import { findQuote } from "@/lib/quotes";
import { indexSources } from "@/lib/sources";

// One quote's own address: the quote, checked, with the article around it and
// the story it belongs to (opengraph-image.tsx beside this file draws the quote
// card). Canonical stays the record, so search does not see a second copy.
export async function generateMetadata({ params }: { params: Promise<{ id: string; n: string }> }): Promise<Metadata> {
  const { id, n } = await params;
  let event;
  try {
    event = await fetchEvent(id);
  } catch {
    return { title: "Story not found" };
  }
  const q = findQuote(event.claims, n);
  if (!q) return { title: event.title };
  const title = `“${q.claim.quote_text.length > 90 ? `${q.claim.quote_text.slice(0, 89)}…` : q.claim.quote_text}” — ${q.speaker}`;
  const description = `${q.speaker}${q.role ? `, ${q.role}` : ""}, as reported by ${q.claim.source_name}. On Prism: ${event.title}`;
  return {
    title,
    description,
    alternates: { canonical: `/story/${id}` },
    openGraph: { type: "article", siteName: "Prism", title, description, url: `/story/${id}/quote/${n}` },
    twitter: { card: "summary_large_image", title, description },
  };
}

/** The record as one story row (ChartRow reads a feed item): its reports' outlets, and its photo only with a credit. */
function rowOf(event: EventDetail): FeedItem {
  const outlets: OutletRef[] = event.sources
    .filter((s, i, all) => s.code && s.origin && all.findIndex((t) => t.source_slug === s.source_slug) === i)
    .map((s) => ({ slug: s.source_slug, publisher: s.publisher ?? s.source_slug, name: s.source_name, code: s.code!, origin: s.origin!, language: s.language ?? null, domain: s.domain ?? null }));
  const photo = event.image_url ? event.sources.find((s) => s.image_url === event.image_url && s.code) : undefined;
  const latest = event.sources.map((s) => s.published_at).filter((t): t is string => Boolean(t)).sort((a, b) => Date.parse(a) - Date.parse(b)).at(-1) ?? null;
  return {
    id: event.id,
    title: event.title,
    headline_lang: null,
    available_languages: [],
    summary: event.summary,
    sector: event.sector,
    subsector: event.subsector,
    regions: event.regions,
    image_url: photo ? event.image_url : null,
    image_outlet: photo ? outlets.find((o) => o.slug === photo.source_slug) ?? null : null,
    is_regional: false,
    coverage: event.coverage,
    event_type: event.projection?.event_type ?? null,
    source_count: event.projection?.source_count ?? event.sources.length,
    cvss_score: event.projection?.cyber?.cvss?.score ?? null,
    cvss_severity: event.projection?.cyber?.cvss?.severity ?? null,
    kev_listed: Boolean(event.projection?.cyber?.exploitation?.kev_listed),
    cve_ids: event.projection?.cyber?.cve_ids ?? [],
    tickers: event.projection?.finance?.tickers ?? [],
    catalyst: event.projection?.finance?.catalyst ?? null,
    price_impact_direction: event.projection?.finance?.price_impact?.direction ?? null,
    last_updated_at: event.last_updated_at,
    latest_published_at: latest,
    score: 0,
    outlets,
  };
}

/**
 * The quote's own page — the share card's target (Claude Design · ReadingB
 * QuotePage): the words in the record voice under a 3px ink rule, who said
 * them, where and when in the provenance voice, the language they were printed
 * in, the check that was made, then the article around them and the story.
 * The check line never claims more than the check did: verbatim is to the
 * ARTICLE, so an outlet's own translation says it is one.
 */
export default async function QuotePage({ params }: { params: Promise<{ id: string; n: string }> }) {
  const { id, n } = await params;
  let event: EventDetail;
  try {
    event = await fetchEvent(id);
  } catch {
    notFound();
  }
  const q = findQuote(event.claims, n);
  if (!q) notFound();
  const { claim, speaker, role } = q;
  const index = indexSources(event.sources).get(claim.article_id);
  const when = claim.published_at ? `${shortDate(claim.published_at)} ${istTime(claim.published_at)} IST` : null;
  const provenance = [claim.source_name.toUpperCase(), index != null ? `[${index}]` : null, when?.toUpperCase()].filter(Boolean).join(" · ");
  const hasContext = Boolean(claim.context_before || claim.context_after);

  return (
    <>
      <div className="contents lg:hidden">
        <BackBar label="Story" href={`/story/${event.id}`} />
      </div>
      <article className="mx-auto grid w-full max-w-[720px] grid-cols-[minmax(0,1fr)] gap-[22px] px-[var(--gutter)] pb-12 pt-5 lg:pt-12">
        <blockquote
          lang={claim.lang ?? undefined}
          className="pl-4 text-pretty [font:italic_400_26px/1.35_var(--font-record)] lg:pl-7 lg:[font:italic_400_38px/1.3_var(--font-record)]"
          style={{ borderLeft: "var(--rule-section) solid var(--ink)", color: "var(--ink)", overflowWrap: "anywhere" }}
        >
          “{claim.quote_text}”
        </blockquote>

        <div className="grid gap-1.5">
          <p style={{ font: "600 17px/1.3 var(--font-read)", overflowWrap: "anywhere" }}>{speaker}</p>
          {/* Who they are, as the articles put it — never a title we supplied. */}
          {role && <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{role}</p>}
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="p-mono" style={{ fontSize: 12, color: "var(--ink-3)" }}>{provenance}</span>
            {claim.lang &&
              (claim.translated ? (
                <span title={`${claim.source_name}'s ${langName(claim.lang)} translation — not the words as spoken`} style={{ font: "500 12.5px/1.2 var(--font-read)", color: "var(--ink-2)" }}>
                  {langNative(claim.lang)} <span className="p-meta__prov">translation</span>
                </span>
              ) : (
                <span className="p-meta__prov" title={`Printed in ${langName(claim.lang)} by ${claim.source_name}`}>{claim.lang.toUpperCase()}</span>
              ))}
          </p>
        </div>

        <p className="flex items-start gap-2" style={{ font: "500 14px/1.4 var(--font-read)", color: "var(--ink-2)" }}>
          <span className="mt-0.5 shrink-0" aria-hidden="true"><Check size={16} /></span>
          {claim.translated ? "Checked against the article. The outlet translated these words." : "Word for word, checked against the article."}
        </p>

        <div className="flex flex-wrap gap-2.5">
          {claim.url && (
            <a href={quoteLink(claim.url, claim.quote_text)} target="_blank" rel="noopener noreferrer" className="p-btn p-btn--primary">
              Open at the quote
              <ArrowUpRight size={16} />
            </a>
          )}
          <div className="inline-flex">
            <ShareButton url={`/story/${event.id}/quote/${n}`} title={`“${claim.quote_text}” — ${speaker}`} label="Share this quote" fill />
          </div>
        </div>

        {hasContext && (
          <section aria-labelledby="in-article" className="grid gap-2">
            <SectionHead id="in-article" title="In the article" />
            <figure className="grid gap-2">
              <p lang={claim.lang ?? undefined} style={{ font: "400 16px/1.7 var(--font-read)", color: "var(--ink-2)", overflowWrap: "anywhere" }}>
                {claim.context_before && <>…{claim.context_before} </>}
                <mark className="rounded-[2px] px-0.5" style={{ background: "var(--accent-soft)", color: "var(--ink)", boxShadow: "inset 0 -2px 0 var(--accent)" }}>{claim.quote_text}</mark>
                {claim.context_after && <> {claim.context_after}…</>}
              </p>
              <figcaption className="p-meta" style={{ font: "500 12.5px/1.3 var(--font-read)" }}>
                {claim.lang && <><span>{langName(claim.lang)}</span><span className="p-meta__sep" /></>}
                <span>{claim.source_name}</span>
              </figcaption>
            </figure>
          </section>
        )}

        <section aria-labelledby="from-story" className="grid grid-cols-[minmax(0,1fr)] gap-2">
          <SectionHead id="from-story" title="From the story" />
          <ol className="grid grid-cols-[minmax(0,1fr)]">
            <ChartRow item={rowOf(event)} />
          </ol>
        </section>
      </article>
    </>
  );
}
