import Link from "next/link";
import { ArrowUpRight } from "@/components/icons";
import { LangLabel, ReportedLabel, Words } from "@/components/Said";
import { SectionHead } from "@/components/SectionHead";
import type { EntityPage } from "@/lib/api";
import { quoteLink } from "@/lib/quoteLink";
import { isReported, quoteProvenance, saidTally } from "@/lib/quotes";

/**
 * "What <name> said" (programmatic SEO P0-3): the quotes the record pages
 * print for this actor, newest first, each set as the record's quote card sets
 * it (Said's Words: italic record voice for a quote, upright on a dashed rule
 * and labelled "reported" for an article's report of what was said) with the
 * quote page's provenance line. The server ran the story page's own checks on
 * every one (api/routes/entity.py), so nothing here is unverified. Absent when
 * there is nothing to show: a section with no data is not drawn (DESIGN.md).
 */
export function EntityQuotes({ page }: { page: EntityPage }) {
  const quotes = page.quotes ?? [];
  if (quotes.length === 0) return null;
  const quoteCount = page.quote_count ?? 0;
  const reportedCount = page.reported_count ?? 0;
  const total = quoteCount + reportedCount;
  const window = page.quotes_window ?? 0;
  // Printed only when the section holds more than one, as the speaker card does.
  const multilingual = new Set(quotes.map((q) => q.lang).filter(Boolean)).size > 1;
  const sub = [
    quotes.length < total ? `${quotes.length} of ${total}` : saidTally(quoteCount, reportedCount),
    quotes.length > 1 && "newest first",
    window > 0 && window < page.record_count && `from the latest ${window} stories`,
  ].filter(Boolean).join(" · ");
  return (
    <section aria-labelledby="entity-said" className="grid grid-cols-[minmax(0,1fr)] gap-3">
      <SectionHead id="entity-said" title={`What ${page.entity.name} said`} sub={sub} />
      <ol className="p-card grid gap-3.5 p-4 sm:p-[18px]">
        {quotes.map((q, i) => (
          <li key={`${q.event_id}-${q.id ?? i}`} className={i > 0 ? "border-t pt-3.5" : ""} style={i > 0 ? { borderColor: "var(--line)" } : undefined}>
            <Words claim={q} font="var(--t-quote)" color="var(--ink)" />
            <p className="mt-2 flex flex-wrap items-center gap-x-2.5 gap-y-0.5 text-[12.5px] font-medium leading-[1.3]" style={{ color: "var(--ink-3)" }}>
              <span className="p-mono" style={{ fontSize: 12 }}>{quoteProvenance(q, q.source_index)}</span>
              {(multilingual || q.translated) && q.lang && <LangLabel claim={q} />}
              {isReported(q) && <ReportedLabel claim={q} />}
            </p>
            <p className="flex flex-wrap items-center gap-x-4 text-[13px] font-semibold">
              {q.url && (
                <a href={quoteLink(q.url, q.quote_text)} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-[44px] items-center gap-1 lg:min-h-[32px]" style={{ color: "var(--accent)" }}>
                  {isReported(q) ? "Open at the line" : "Open at the quote"} <ArrowUpRight size={13} />
                </a>
              )}
              {/* The quote's own page canonicalises to its record: a follow link would spend the crawl on a duplicate. */}
              {q.id && (
                <Link href={`/story/${q.event_id}/quote/${q.id}`} rel="nofollow" className="inline-flex min-h-[44px] items-center lg:min-h-[32px]" style={{ color: "var(--ink-2)" }}>
                  How it was checked
                </Link>
              )}
            </p>
            <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)", overflowWrap: "anywhere" }}>
              From <Link href={`/story/${q.event_id}`} className="underline underline-offset-2">{q.event_title}</Link>
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
