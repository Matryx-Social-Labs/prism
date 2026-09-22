// Structured data for search engines and answer engines, in one place so every
// page says the same thing about who Prism is. Nothing here invents a fact:
// every field is read from the API payload the page already renders, and a
// publisher's photograph is never declared as ours (DESIGN.md § Images).
import type { EntityRef, EventDetail, FeedItem, TrendingStory, TrendingStoryDetail } from "@/lib/api";
import { CONTACT_EMAIL, LEGAL_ENTITY } from "@/lib/legal";
import { SITE_URL } from "@/lib/site";

export const ORG_ID = `${SITE_URL}/#organization`;
export const SITE_ID = `${SITE_URL}/#website`;

/** Who publishes this. `legalName` is the LLP; the brand is Prism. */
export const ORGANIZATION = {
  "@type": "NewsMediaOrganization",
  "@id": ORG_ID,
  name: "Prism",
  legalName: LEGAL_ENTITY,
  url: `${SITE_URL}/`,
  logo: { "@type": "ImageObject", url: `${SITE_URL}/brand/prism-mark-512.png`, width: 512, height: 512 },
  description: "One live story record from monitored Indian and international outlets: every development, verified quote and source open to inspection.",
  areaServed: { "@type": "Country", name: "India" },
  knowsLanguage: ["en", "hi", "kn", "ta", "te"],
  // What we do and refuse to do, in the vocabulary engines read: no invented
  // numbers, quotes verbatim or absent — the /about page says it at length.
  publishingPrinciples: `${SITE_URL}/about`,
  correctionsPolicy: `${SITE_URL}/about#status`,
  contactPoint: { "@type": "ContactPoint", email: CONTACT_EMAIL, contactType: "editorial" },
};

export const WEBSITE = {
  "@type": "WebSite",
  "@id": SITE_ID,
  url: `${SITE_URL}/`,
  name: "Prism",
  publisher: { "@id": ORG_ID },
  inLanguage: "en-IN",
  potentialAction: {
    "@type": "SearchAction",
    target: { "@type": "EntryPoint", urlTemplate: `${SITE_URL}/search?q={search_term_string}` },
    "query-input": "required name=search_term_string",
  },
};

export function siteGraph() {
  return { "@context": "https://schema.org", "@graph": [ORGANIZATION, WEBSITE] };
}

const clip = (s: string, n = 200) => (s.length > n ? `${s.slice(0, n - 3).trimEnd()}…` : s);

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
  // one graph instead of two mentions of a string.
  const about = (event.entities ?? []).slice(0, 12).map((e) =>
    e.slug
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
    datePublished: event.occurred_at ?? event.last_updated_at,
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
    author: { "@id": ORG_ID },
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
    description: clip(`${s.source_count} outlets · ${s.developments.length} developments — ${devs[0]?.title ?? s.label}`),
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
