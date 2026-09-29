// Structured data for search engines and answer engines, in one place so every
// page says the same thing about who Prism is. Nothing here invents a fact:
// every field is read from the API payload the page already renders, and a
// publisher's photograph is never declared as ours (DESIGN.md § Images).
import type { EntityQuote, EntityRef, EventDetail, FeedItem, TrendingStory, TrendingStoryDetail } from "@/lib/api";
import { isReported } from "@/lib/quotes";
import { CONTACT_EMAIL, LEGAL_ENTITY } from "@/lib/legal";
import { SITE_URL } from "@/lib/site";

export const ORG_ID = `${SITE_URL}/#organization`;

/**
 * A page that stays readable and linked but asks not to be indexed: a record
 * from one outlet, a provisional story (Search Console, 2026-09-21 — 13 of the
 * 19 records it would not index were one-outlet rewrites; 4 stories named one
 * event in the URL and showed another). `follow`, so its links still count.
 */
export const NOT_INDEXED = { index: false, follow: true } as const;

/**
 * Spread into a page's metadata: `{ robots: NOT_INDEXED }` when it should not
 * be indexed, and NOTHING otherwise. Never `robots: undefined` — Next does not
 * fall back to the layout's robots for an explicit undefined, it erases them,
 * and with them max-image-preview:large and max-snippet (every indexable
 * record, actor and subject page shipped no robots meta until 2026-09-27).
 */
export function robotsUnless(indexable: boolean): { robots?: typeof NOT_INDEXED } {
  return indexable ? {} : { robots: NOT_INDEXED };
}

/**
 * rel for a link to a record or a story: "nofollow" where that page asks not
 * to be indexed, so a hub spends its follow links on pages that can rank
 * (entityRel is the same rule for actors). A record asks from its second
 * outlet (`indexable`); a story once its boundary is verified. Unknown (an
 * older payload): plain. 49–58 of a hub's 60 row links pointed at one-outlet
 * records Google then drops (audit A3). Records that gain an outlet are still
 * found through records-sitemap.xml and IndexNow, which read the same rule.
 */
export function followRel(indexable: boolean | undefined): "nofollow" | undefined {
  return indexable === false ? "nofollow" : undefined;
}
export const SITE_ID = `${SITE_URL}/#website`;

/** Who publishes this. `legalName` is the LLP; the brand is Prism. */
export const ORGANIZATION = {
  "@type": "NewsMediaOrganization",
  "@id": ORG_ID,
  name: "Prism",
  // "Prism" alone names several products; the address is ours alone.
  alternateName: "readprism.news",
  legalName: LEGAL_ENTITY,
  url: `${SITE_URL}/`,
  logo: { "@type": "ImageObject", url: `${SITE_URL}/brand/prism-mark-512.png`, width: 512, height: 512 },
  description: "India's verifiable news record: one record per story from a public list of monitored Indian outlets, with every report, verbatim quote and source open to inspection.",
  areaServed: { "@type": "Country", name: "India" },
  // What we do and refuse to do, in the vocabulary engines read: no invented
  // numbers, quotes verbatim or absent — the /about page says it at length.
  // "Who writes this, and how to correct it" answers all three: records are
  // written by machine and say so, and a mistake has a public way in. No
  // verificationFactCheckingPolicy: Prism checks quotes are verbatim, not that
  // claims are true. No knowsLanguage: a typed list drifts from /sources.
  publishingPrinciples: `${SITE_URL}/about`,
  correctionsPolicy: `${SITE_URL}/about#accountability`,
  actionableFeedbackPolicy: `${SITE_URL}/about#accountability`,
  noBylinesPolicy: `${SITE_URL}/about#accountability`,
  contactPoint: { "@type": "ContactPoint", email: CONTACT_EMAIL, contactType: "editorial" },
};

export const WEBSITE = {
  "@type": "WebSite",
  "@id": SITE_ID,
  url: `${SITE_URL}/`,
  name: "Prism",
  alternateName: "readprism.news",
  publisher: { "@id": ORG_ID },
  inLanguage: "en-IN",
  potentialAction: {
    "@type": "SearchAction",
    target: { "@type": "EntryPoint", urlTemplate: `${SITE_URL}/search?q={search_term_string}` },
    "query-input": "required name=search_term_string",
  },
};

/**
 * A page's own share card: its title, description and address. The layout
 * sets only the site name and card type, so a page that forgets this falls
 * back to its own <title> instead of claiming to be the homepage (audit
 * 2026-09-29: eleven page types shared as the landing).
 */
export function social(title: string, description: string, path: string) {
  return {
    openGraph: { type: "website" as const, siteName: "Prism", locale: "en_IN", title, description, url: path },
    twitter: { card: "summary_large_image" as const, title, description },
  };
}

export function siteGraph() {
  return { "@context": "https://schema.org", "@graph": [ORGANIZATION, WEBSITE] };
}

const clip = (s: string, n = 200) => (s.length > n ? `${s.slice(0, n - 3).trimEnd()}…` : s);

/** When the first of a record's reports was published, or null. */
export function firstReportedAt(event: EventDetail): string | null {
  return (event.sources ?? []).map((s) => s.published_at).filter((t): t is string => Boolean(t)).sort((a, b) => Date.parse(a) - Date.parse(b))[0] ?? null;
}

export function eventDescription(event: EventDetail): string {
  return clip(event.summary ?? event.lens_briefs?.reader ?? event.title);
}

/**
 * A record as a NewsArticle. `isBasedOn` lists the reports it is written from
 * — the grounding an answer engine can follow — and `about` the named
 * entities. The image is the record's OWN card (opengraph-image.tsx), never
 * the publisher's photograph: Top Stories and Discover weigh `image`, and
 * without one the record was not eligible (audit H28).
 */
export function newsArticleLd(event: EventDetail) {
  const url = `${SITE_URL}/story/${event.id}`;
  const sources = (event.sources ?? []).filter((s) => s.url);
  // `about` names the actors AND addresses them: an engine that follows the id
  // lands on the hub page that carries the same @id, so record and hub read as
  // one graph instead of two mentions of a string. A stub (noindex) is named,
  // not addressed: its URL here only sent crawlers to a page they must drop.
  const about = (event.entities ?? []).slice(0, 12).map((e) =>
    e.slug && e.indexable !== false
      ? { "@type": "Thing", name: e.name, "@id": `${SITE_URL}/entity/${e.slug}#entity`, url: `${SITE_URL}/entity/${e.slug}` }
      : { "@type": "Thing", name: e.name },
  );
  return {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    "@id": `${url}#article`,
    mainEntityOfPage: { "@type": "WebPage", "@id": url },
    url,
    headline: clip(event.title, 110),
    description: eventDescription(event),
    // The first report's time: a timestamp, not occurred_at's bare date, and it
    // never moves forward as outlets are added (the news sitemap uses the same).
    datePublished: firstReportedAt(event) ?? event.occurred_at ?? event.last_updated_at,
    dateModified: event.last_updated_at,
    inLanguage: "en-IN",
    isAccessibleForFree: true,
    image: [{ "@type": "ImageObject", url: `${url}/opengraph-image`, width: 1200, height: 630 }],
    articleSection: event.sector ?? undefined,
    keywords: [...new Set([event.sector, ...(event.entities ?? []).map((e) => e.name)].filter(Boolean))].slice(0, 20).join(", ") || undefined,
    about: about.length ? about : undefined,
    isBasedOn: sources.slice(0, 12).map((s) => ({
      "@type": "NewsArticle",
      url: s.url,
      headline: clip(s.title, 110),
      datePublished: s.published_at ?? undefined,
      inLanguage: s.language ?? undefined,
      // `source_name` is the outlet's display name ("The Times of India");
      // `publisher` is the registry key and reads as a slug.
      publisher: { "@type": "Organization", name: s.source_name, ...(s.domain ? { url: `https://${s.domain}/` } : {}) },
    })),
    // Named inline as well: a reader of this block alone still gets the author.
    author: { "@type": "Organization", "@id": ORG_ID, name: "Prism", url: `${SITE_URL}/about` },
    publisher: { "@id": ORG_ID },
  };
}

/**
 * An actor as itself, with the records naming it as its `subjectOf`. The type
 * is the server's mapping of the extractor's loose vocabulary (Person,
 * Organization, Place…), defaulting to Thing rather than asserting something
 * false about a person. `sameAs` carries the Wikidata item where one is known —
 * the one fact that lets an engine merge this page with the entity it knows.
 */
export function entityLd(entity: EntityRef, url: string, recordCount: number) {
  return {
    "@context": "https://schema.org",
    "@type": entity.schema_type,
    "@id": `${url}#entity`,
    name: entity.name,
    url,
    ...(entity.aliases.length ? { alternateName: entity.aliases.slice(0, 8) } : {}),
    ...(entity.qid ? { sameAs: [`https://www.wikidata.org/wiki/${entity.qid}`] } : {}),
    description: `${recordCount} Prism ${recordCount === 1 ? "record names" : "records name"} ${entity.name}.`,
    mainEntityOfPage: { "@type": "WebPage", "@id": url },
  };
}

/**
 * "What <name> said" for answer engines, as entityLd's `subjectOf`: the direct
 * quotes the page prints, each a Quotation attributed to the entity's @id and
 * grounded in the article that printed it. Words an article only REPORTED are
 * not quotations and are left out, as the page never styles them as one. Null
 * when no quote is left.
 */
export function quotationsLd(quotes: EntityQuote[], url: string) {
  const said = quotes.filter((q) => !isReported(q));
  if (said.length === 0) return null;
  return {
    "@type": "ItemList",
    "@id": `${url}#quotes`,
    numberOfItems: said.length,
    itemListElement: said.map((q, i) => ({
      "@type": "ListItem",
      position: i + 1,
      item: {
        "@type": "Quotation",
        text: q.quote_text,
        spokenByCharacter: { "@id": `${url}#entity` },
        ...(q.id ? { url: `${SITE_URL}/story/${q.event_id}/quote/${q.id}` } : {}),
        ...(q.url ? { isBasedOn: q.url } : {}),
        ...(q.published_at ? { datePublished: q.published_at } : {}),
        ...(q.lang ? { inLanguage: q.lang } : {}),
      },
    })),
  };
}

/** Home → subject → record, so an engine can place a record in the hierarchy. */
export function breadcrumbLd(trail: { name: string; url: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: trail.map((t, i) => ({ "@type": "ListItem", position: i + 1, name: t.name, item: t.url })),
  };
}

/** A developing story: the arc as an article whose parts are its developments. */
export function storyLd(s: TrendingStoryDetail) {
  const url = `${SITE_URL}/trending/${s.canonical_slug}`;
  const devs = [...s.developments].sort((a, b) => (a.occurred_at ?? "").localeCompare(b.occurred_at ?? ""));
  const first = devs.find((d) => d.occurred_at)?.occurred_at;
  const last = [...devs].reverse().find((d) => d.occurred_at)?.occurred_at;
  return {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    "@id": `${url}#story`,
    mainEntityOfPage: { "@type": "WebPage", "@id": url },
    url,
    headline: clip(s.label, 110),
    description: clip(`${s.source_count} outlets · ${s.developments.length} ${s.boundary_status === "verified" ? "developments" : "records"} — ${devs[0]?.title ?? s.label}`),
    datePublished: first ?? last ?? undefined,
    dateModified: last ?? first ?? undefined,
    inLanguage: "en-IN",
    isAccessibleForFree: true,
    articleSection: s.sector ?? undefined,
    about: (s.cast ?? []).slice(0, 12).map((name) => ({ "@type": "Thing", name })),
    hasPart: devs.slice(0, 40).map((d) => ({
      "@type": "NewsArticle",
      url: `${SITE_URL}/story/${d.id}`,
      headline: clip(d.title, 110),
      datePublished: d.occurred_at ?? undefined,
    })),
    author: { "@id": ORG_ID },
    publisher: { "@id": ORG_ID },
  };
}

/** The day's record or the developing stories as an ItemList of links. */
export function itemListLd(name: string, pageUrl: string, items: { url: string; name: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "ItemList",
    "@id": `${pageUrl}#list`,
    name,
    url: pageUrl,
    numberOfItems: items.length,
    itemListElement: items.slice(0, 60).map((it, i) => ({ "@type": "ListItem", position: i + 1, url: it.url, name: clip(it.name, 110) })),
  };
}

export const feedListItems = (items: FeedItem[]) => items.map((e) => ({ url: `${SITE_URL}/story/${e.id}`, name: e.title }));
export const storyListItems = (stories: TrendingStory[]) => stories.map((s) => ({ url: `${SITE_URL}/trending/${s.slug}`, name: s.label ?? s.hero_title ?? s.slug }));

/**
 * Serialise for a <script type="application/ld+json">. JSON.stringify handles
 * quotes and backslashes but not the closing-tag sequence, so a headline
 * containing `</script>` would break out of the element; titles come from
 * scraped publisher copy and LLM extraction, so they are not trusted input.
 */
export function jsonLd(data: unknown): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}

/** Questions and answers exactly as the page shows them (lib/faq). */
export function faqLd(items: { q: string; a: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map(({ q, a }) => ({ "@type": "Question", name: q, acceptedAnswer: { "@type": "Answer", text: a } })),
  };
}
