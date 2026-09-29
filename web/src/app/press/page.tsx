import type { Metadata } from "next";
import Link from "next/link";
import { REFUSALS } from "@/components/HowItWorks";
import { ArrowDown } from "@/components/icons";
import { PageTitle } from "@/components/reading/parts";
import { SectionHead } from "@/components/SectionHead";
import { BackBar } from "@/components/ui";
import { fetchSources } from "@/lib/api";
import { CONTACT_EMAIL, LEGAL_CITY, LEGAL_ENTITY, LEGAL_PARTNER } from "@/lib/legal";
import { social } from "@/lib/seo";

// The press kit (.context/marketing/05 §6.1): what Prism is in one paragraph,
// how it works, the rules, who publishes it, who to write to, how to cite, and
// the logo files. Nothing typed that the code or the API cannot show: the
// paragraph and the citation lines are /llms.txt's (a test fails if they
// drift), the rules are /about's, the counts are the API's or absent. Founder
// bios, headshots and screenshots are not here until they exist.
export const revalidate = 300; // the monitored list's own clock (fetchSources)

const title = "Press";
const description = "Prism for journalists: what it is in one paragraph, how to cite a record and a quote, the logo files, and who to write to.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/press" },
  ...social(title, description, "/press"),
};

/** Ready to copy; the same words as /llms.txt. */
const PRESS_PARAGRAPH =
  "Prism (readprism.news) is India's verifiable news record: one record per news story, built from the reports of a public list of monitored Indian and international outlets, in English and Indian languages. Every report, verbatim quote and source is open to inspection. Published by Prism Media Intelligence LLP; built with Matrix Social Labs.";

/** How to cite, as /llms.txt says it. */
const CITE_RECORD = 'Cite a record as: Prism, "<headline>", readprism.news/story/<id>, and name the outlets it lists as its sources. The record is a synthesis of their reporting, not a primary source.';
const CITE_QUOTE = "A quote has its own address, readprism.news/story/<id>/quote/<n>: the words, the speaker, the outlet, and a link that opens the article at that line.";

const HOW = [
  "Prism reads the public feeds of a fixed, public list of Indian and international outlets, in English and Indian languages.",
  "The reports of one story become one record, and every report on it links to its outlet.",
  "A record counts the monitored outlets that reported the story, out of the whole list, and marks a story one outlet carries as not yet corroborated.",
  "A quote appears only if the article prints the same words inside quotation marks; speech an Indian-language article reports without them is labelled “reported”.",
  "Headlines, summaries and briefs are written by software from the listed reports, and every page says so. A correction is public, with its date and reason.",
];

// The files are design/logo/wordmark.py's exports of the mark and Brand's lockup.
// Their previews sit on the ground each is made for, whatever the page's theme.
const GROUND = { light: "#F7F6F2", dark: "#0F1114" } as const;
// `w` is the file's own width on its 24-unit box, so the preview keeps its shape.
const ASSETS = [
  { what: "The lockup", file: "readprism-lockup", alt: "readPrism.news", w: 183, max: 240 },
  { what: "The mark", file: "prism-mark", alt: "Prism", w: 24, max: 56 },
] as const;

const para = { font: "var(--t-body)", color: "var(--ink-2)" } as const;

function Asset({ what, file, alt, w, max, ground }: (typeof ASSETS)[number] & { ground: keyof typeof GROUND }) {
  const name = `${file}-on-${ground}`;
  const label = `${what}, for ${ground} grounds`;
  return (
    <figure className="m-0 grid gap-2">
      <div className="grid place-items-center px-4 py-7" style={{ background: GROUND[ground], border: "1px solid var(--line)", borderRadius: "var(--r-record)" }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={`/brand/${name}.svg`} alt={alt} width={w} height={24} style={{ width: "100%", maxWidth: max, height: "auto" }} />
      </div>
      <figcaption className="flex flex-wrap items-center gap-x-3" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
        <span className="mr-auto">For {ground} grounds</span>
        {(["svg", "png"] as const).map((ext) => (
          <a key={ext} href={`/brand/${name}.${ext}`} download className="p-link inline-flex min-h-[44px] items-center gap-1" aria-label={`${label}, ${ext.toUpperCase()}`}>
            {ext.toUpperCase()} <ArrowDown size={13} />
          </a>
        ))}
      </figcaption>
    </figure>
  );
}

export default async function PressPage() {
  const set = await fetchSources();
  const languages = set ? new Set(set.feeds.map((f) => f.language ?? "en")).size : 0;
  return (
    <>
      <div className="contents lg:hidden">
        <BackBar label="Today" href="/feed" />
      </div>
      <div className="mx-auto grid w-full max-w-[720px] grid-cols-[minmax(0,1fr)] gap-7 px-[var(--gutter)] pb-16 pt-5 lg:pt-10">
        <header className="grid gap-3">
          <PageTitle>Press</PageTitle>
          <p className="max-w-[60ch] text-pretty" style={{ font: "var(--t-body-l)", color: "var(--ink)" }}>{PRESS_PARAGRAPH}</p>
          {set && set.outlets > 0 && (
            <p className="flex flex-wrap items-baseline gap-x-2">
              <span className="p-eyebrow">On the record today</span>
              <Link href="/sources" className="p-count" style={{ color: "var(--ink-2)" }}>
                {set.outlets} monitored outlets · {languages} languages
              </Link>
            </p>
          )}
        </header>

        <section aria-labelledby="how" className="grid gap-3">
          <SectionHead id="how" title="How it works" />
          <ol className="grid list-decimal gap-2 pl-5" style={para}>
            {HOW.map((line) => <li key={line}>{line}</li>)}
          </ol>
          <p style={{ font: "var(--t-body-s)" }}><Link href="/about" className="p-link">One real story, followed step by step →</Link></p>
        </section>

        <section aria-labelledby="rules" className="grid gap-3">
          <SectionHead id="rules" title="The rules it keeps" />
          <ul className="grid gap-1.5" style={para}>
            {REFUSALS.map(([rule]) => <li key={rule}>{rule}</li>)}
          </ul>
          <p style={{ font: "var(--t-body-s)" }}><Link href="/about#refuses" className="p-link">Each rule, and why →</Link></p>
        </section>

        <section aria-labelledby="who" className="grid gap-3">
          <SectionHead id="who" title="Who publishes it" />
          <p className="max-w-[60ch]" style={para}>
            Prism is published by {LEGAL_ENTITY}, {LEGAL_CITY}. {LEGAL_PARTNER} builds and runs it as its technology partner. Prism does not report:
            the journalism on a record is the outlets&rsquo;, and every record names them.
          </p>
          <p style={{ font: "var(--t-body-s)" }}><Link href="/about#accountability" className="p-link">Who writes a record, and how to correct it →</Link></p>
        </section>

        <section aria-labelledby="contact" className="grid gap-3">
          <SectionHead id="contact" title="Press contact" />
          <p className="max-w-[60ch]" style={para}>
            Write to <a href={`mailto:${CONTACT_EMAIL}`} className="p-link">{CONTACT_EMAIL}</a>. A complaint about something on Prism goes to the
            Grievance Officer instead, who has a clock to answer it: <Link href="/grievance" className="p-link">Grievances</Link>.
          </p>
        </section>

        <section aria-labelledby="cite" className="grid gap-3">
          <SectionHead id="cite" title="How to cite a record and a quote" />
          <ul className="grid gap-2" style={para}>
            <li>{CITE_RECORD}</li>
            <li>{CITE_QUOTE}</li>
          </ul>
        </section>

        <section aria-labelledby="assets" className="grid gap-4">
          <SectionHead id="assets" title="Logo files" hint="SVG and PNG, on transparent grounds; each file is named for the ground it goes on." />
          {ASSETS.map((a) => (
            <div key={a.file} className="grid gap-2">
              <h3 style={{ font: "var(--t-title-s)" }}>{a.what}</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <Asset {...a} ground="light" />
                <Asset {...a} ground="dark" />
              </div>
            </div>
          ))}
          <ul className="grid gap-1.5" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
            <li>The lockup is the address: readPrism.news, one word, as drawn. Don&rsquo;t add a space, capitalise the R or set it on two lines.</li>
            <li>In running text the name is Prism and the address is readprism.news, lowercase.</li>
            <li>Keep the mark&rsquo;s colours; the spectrum band is its only colour. Below 16 pixels, use the mark alone.</li>
          </ul>
        </section>
      </div>
    </>
  );
}
