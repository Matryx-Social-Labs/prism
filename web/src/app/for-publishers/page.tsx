import type { Metadata } from "next";
import Link from "next/link";
import { PageTitle } from "@/components/reading/parts";
import { SectionHead } from "@/components/SectionHead";
import { BackBar } from "@/components/ui";
import { grievanceHref } from "@/lib/grievance";
import { CONTACT_EMAIL, GRIEVANCE_OFFICER } from "@/lib/legal";
import { social } from "@/lib/seo";

// For the outlets Prism reads (.context/marketing/05 §3.2, 06 §2.18): what it
// takes from a report, what it sends back, and how to have something corrected
// or removed. Every line is what the code does, and where:
//   reads      the public feed; the article at its address (enrichment/fulltext.py)
//   keeps      the text, for the quote check (enrichment/claims.py), the summary
//              and the question box (agent/rag.py); no page prints the article
//   shows      headline, outlet, time, link (components/SourceList.tsx); a quote
//              only when verbatim, with at most CONTEXT_CHARS (220) either side
//              (api/routes/events.py quote_context), opening the article at the
//              line (lib/quoteLink.ts); the photo from the outlet's own server,
//              credited, beside "Their report" (PhotoImg, PhotoDeck), behind
//              the switch (lib/images.ts REPORT_IMAGES), never on a share card
//              (lib/ogCard.tsx), never stored (common/imagehash.py)
//   sends back isBasedOn in the record's structured data (lib/seo.ts)
// Change this page in the same commit as any of those.
const title = "For publishers";
const description = "For the outlets Prism reads: what Prism takes from a report, what it sends back, and how to have a record corrected or an outlet removed.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/for-publishers" },
  ...social(title, description, "/for-publishers"),
};

const TAKES: [string, string][] = [
  ["Your headline, your name, your time, your link.", "A record lists each report as you published it: the headline, the outlet and its mark, the time, and a link to the article."],
  ["A quote only if it is your article's words.", "A quote appears only when the article prints the same words inside quotation marks, and it is checked against the article before it appears. Beside it, folded under “In the article”, sit at most 220 characters of the article either side of it, so a reader can see it in place. In an Indian-language article, speech reported without quotation marks is labelled “reported”, never set as a quote."],
  ["Your photograph, only as a credited preview.", "A report’s lead photograph can appear as a preview credited to your outlet. It loads from the address you published it at; Prism does not keep a copy. On a record it sits beside a link to your report, and one setting turns every photograph on Prism off. Share cards never carry one."],
  ["What Prism writes, it labels as its own.", "A record’s headline, summary and brief are written by software from all the reports listed under it, and the page says so. Nothing Prism writes is presented as your reporting."],
];

const SENDS: [string, string][] = [
  ["Every report, quote and photo on a record links to you.", "A report opens your article; a quote opens it at that line; a photograph sits beside “Their report”."],
  ["Search engines see where a record comes from.", "Each record’s structured data names the reports it was written from, with their outlets."],
  ["Counted, never rated.", "A record says how many monitored outlets reported the story, out of the public list. Prism rates no outlet’s politics and no report’s tone."],
];

const para = { font: "var(--t-body)", color: "var(--ink-2)" } as const;

function Ruled({ items }: { items: [string, string][] }) {
  return (
    <ul className="grid gap-4">
      {items.map(([head, body]) => (
        <li key={head} className="grid gap-1 border-t pt-3" style={{ borderColor: "var(--line)" }}>
          <p style={{ font: "var(--t-title-s)", color: "var(--ink)" }}>{head}</p>
          <p className="max-w-[60ch]" style={para}>{body}</p>
        </li>
      ))}
    </ul>
  );
}

export default function ForPublishersPage() {
  return (
    <>
      <div className="contents lg:hidden">
        <BackBar label="Today" href="/feed" />
      </div>
      <div className="mx-auto grid w-full max-w-[720px] grid-cols-[minmax(0,1fr)] gap-7 px-[var(--gutter)] pb-16 pt-5 lg:pt-10">
        <header className="grid gap-2">
          <PageTitle>For the outlets Prism reads</PageTitle>
          <p className="max-w-[60ch] text-pretty" style={para}>
            Prism is built on your reporting. It does not report: it reads what monitored outlets publish, keeps one record per story, and sends
            its readers to the reports. This page says what it takes, what it sends back, and how to have something corrected or removed.
          </p>
        </header>

        <section aria-labelledby="reads" className="grid gap-3">
          <SectionHead id="reads" title="What Prism reads" />
          <p className="max-w-[60ch]" style={para}>
            Your public feed, every few minutes. For each item it takes onto the record, it reads the article at its public address and keeps
            the text: to check quotes against it, to write the record&rsquo;s summary, and to answer readers&rsquo; questions about the story. No page
            on Prism prints your article.
          </p>
        </section>

        <section aria-labelledby="takes" className="grid gap-3">
          <SectionHead id="takes" title="What a record shows from your report" />
          <Ruled items={TAKES} />
        </section>

        <section aria-labelledby="sends" className="grid gap-3">
          <SectionHead id="sends" title="What it sends back" />
          <Ruled items={SENDS} />
        </section>

        <section aria-labelledby="fix" className="grid gap-3">
          <SectionHead id="fix" title="Corrections and removal" />
          <p className="max-w-[60ch]" style={para}>
            If a record gets your report wrong (a quote, a fact, which outlet carried it), use the{" "}
            <Link href={grievanceHref("An outlet says something different")} className="p-link">grievance form</Link> or write to{" "}
            <a href={`mailto:${GRIEVANCE_OFFICER.email}`} className="p-link">{GRIEVANCE_OFFICER.email}</a>. The Grievance Officer acknowledges a
            complaint within 24 hours and decides it within 15 days.
          </p>
          <p className="max-w-[60ch]" style={para}>
            To ask for your outlet to be taken off the list Prism reads, or anything else, write to{" "}
            <a href={`mailto:${CONTACT_EMAIL}`} className="p-link">{CONTACT_EMAIL}</a>.
          </p>
          <p className="max-w-[60ch]" style={para}>
            A correction is public: the record says what was wrong and when, keeps every earlier version, and is listed on{" "}
            <Link href="/corrections" className="p-link">Corrections</Link>.
          </p>
        </section>

        <section aria-labelledby="list" className="grid gap-3">
          <SectionHead id="list" title="The list" />
          <p className="max-w-[60ch]" style={para}>
            Every outlet Prism reads is public, by origin and language, with when each was last read. Every count on a record is out of it.
          </p>
          <p style={{ font: "var(--t-body-s)" }}><Link href="/sources" className="p-link">The outlets Prism reads →</Link></p>
        </section>
      </div>
    </>
  );
}
