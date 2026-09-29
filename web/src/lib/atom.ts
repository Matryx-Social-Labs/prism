import { SITE_URL } from "@/lib/site";

/** One record as /api/v1/sitemap/atom sends it: already the indexable ones, newest report first. */
export interface AtomRecord {
  id: string;
  title: string;
  /** The record's own summary (written by Prism from the reports), never article text. */
  summary: string | null;
  /** The newest report's publication, clamped to Prism's own rebuild of the record. */
  updated: string;
}

export const FEED_TITLE = "Prism: India's verifiable news record";
const FEED_SUBTITLE = "The newest records two or more monitored outlets reported. Every count on a record is out of the public list at readprism.news/sources.";

// XML 1.0 refuses these characters outright, so one stray control byte in a
// headline would make a reader reject the whole feed.
const NOT_XML = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\uFFFE\uFFFF]/g;
export const xmlEscape = (s: string) =>
  s.replace(NOT_XML, "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");

const iso = (t: string | number) => new Date(t).toISOString();

function entry(r: AtomRecord): string {
  const url = xmlEscape(`${SITE_URL}/story/${r.id}`);
  return `  <entry>
    <id>${url}</id>
    <title>${xmlEscape(r.title)}</title>
    <link rel="alternate" type="text/html" href="${url}"/>
    <updated>${iso(r.updated)}</updated>
    <author><name>Prism</name></author>${r.summary ? `\n    <summary>${xmlEscape(r.summary)}</summary>` : ""}
  </entry>`;
}

/**
 * The Atom document (RFC 4287) for /feed.xml. A record whose time does not
 * parse is left out rather than stamped with an invented one; the feed's own
 * `updated` is its newest entry's, or now when there is none.
 */
export function atomFeed(records: AtomRecord[]): string {
  const dated = records.filter((r) => r.id && r.title && Number.isFinite(Date.parse(r.updated)));
  const updated = iso(dated.length ? Math.max(...dated.map((r) => Date.parse(r.updated))) : Date.now());
  return `<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>${SITE_URL}/feed.xml</id>
  <title>${xmlEscape(FEED_TITLE)}</title>
  <subtitle>${xmlEscape(FEED_SUBTITLE)}</subtitle>
  <link rel="self" type="application/atom+xml" href="${SITE_URL}/feed.xml"/>
  <link rel="alternate" type="text/html" href="${SITE_URL}/feed"/>
  <updated>${updated}</updated>
  <author><name>Prism</name><uri>${SITE_URL}/</uri></author>
  <icon>${SITE_URL}/brand/prism-mark-64.png</icon>
${dated.map(entry).join("\n")}
</feed>
`;
}
