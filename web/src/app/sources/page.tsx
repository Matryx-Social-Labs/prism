import type { Metadata } from "next";
import Link from "next/link";
import { CoverageBar, OutletIcon } from "@/components/Coverage";
import { PageTitle } from "@/components/reading/parts";
import { SectionHead } from "@/components/SectionHead";
import { Alert, BackBar, InShortCard } from "@/components/ui";
import { fetchSources, type MonitoredFeed, type OutletRef } from "@/lib/api";
import { ORIGINS, ORIGIN_LABEL } from "@/lib/coverage";
import { relativeTime } from "@/lib/dateline";
import { langName } from "@/lib/languages";
import { stateName } from "@/lib/regions";
import { missingLanguages } from "@/lib/sources";

// The monitored set, in public: every outlet Prism reads, and when each was
// last read. Every count on a record ("2 of 27 monitored outlets") is out of
// this list, and nothing here is operational (no feed address, no error text).
// Claude Design · ReadingB Sources: grouped by origin in the coverage bar's
// slot order, each group counted, the whole set drawn as one bar on top.
export const revalidate = 300;

export const metadata: Metadata = {
  title: "The outlets Prism reads",
  description: "Every outlet Prism monitors, by origin and language, with when each was last read. Every count on a Prism record is out of this list.",
  alternates: { canonical: "/sources" },
};

const plural = (n: number, one: string) => `${n} ${one}${n === 1 ? "" : "s"}`;

function FeedRow({ feed }: { feed: MonitoredFeed }) {
  const notes = [feed.state && `${stateName(feed.state) ?? feed.state} desk`, feed.sector && `${feed.sector} only`, feed.official && "Official releases"].filter(Boolean);
  const lang = feed.language ?? "en";
  return (
    // State is line form, in words: a feed that has not answered in the last
    // hour sits on a dashed rule and says since when.
    <li className="grid grid-cols-[28px_minmax(0,1fr)_auto] items-center gap-3 py-2.5" style={{ borderBottom: `1px ${feed.reachable ? "solid" : "dashed"} var(${feed.reachable ? "--line" : "--line-strong"})` }}>
      <OutletIcon domain={feed.domain} code={feed.code} name={feed.name} size={24} />
      <span className="min-w-0">
        <span className="block" style={{ font: "var(--t-ui)", overflowWrap: "anywhere" }}>{feed.name}</span>
        {notes.length > 0 && <span className="block" style={{ font: "400 13px/1.4 var(--font-read)", color: "var(--ink-3)" }}>{notes.join(" · ")}</span>}
      </span>
      <span className="grid justify-items-end gap-0.5 text-right">
        <span className="p-meta__prov" title={langName(lang)}>{lang.toUpperCase()}</span>
        <span className="p-mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
          {feed.reachable && feed.checked_at ? `Read ${relativeTime(feed.checked_at)}` : feed.ok_at ? `Not reached since ${relativeTime(feed.ok_at)}` : "Not reached yet"}
        </span>
      </span>
    </li>
  );
}

export default async function SourcesPage() {
  const set = await fetchSources();
  const feeds = set?.feeds ?? [];
  const languages = new Set(feeds.map((f) => f.language ?? "en")).size;
  const missing = set ? missingLanguages(feeds) : [];
  // One entry per masthead, for the bar: several feeds from one outlet count once.
  const mastheads: OutletRef[] = feeds
    .filter((f, i) => feeds.findIndex((g) => g.publisher === f.publisher) === i)
    .map((f) => ({ slug: f.slug, publisher: f.publisher, name: f.name, code: f.code, origin: f.origin, language: f.language }));
  const denominator = set?.outlets ?? "N";
  return (
    <>
      <div className="contents lg:hidden">
        <BackBar label="Today" href="/feed" />
      </div>
      <div className="mx-auto grid w-full max-w-[820px] grid-cols-[minmax(0,1fr)] gap-5 px-[var(--gutter)] pb-16 pt-5 lg:pt-10">
        <header className="grid gap-2">
          <PageTitle>The outlets Prism reads</PageTitle>
          <p className="max-w-[60ch] text-pretty" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
            Every count on a record is out of this list. When a story says <em>2 of {denominator} monitored outlets</em>, these are the {set?.outlets ?? "outlets"} it means, not everyone who covered it. Prism reads each outlet&rsquo;s public feed every few minutes; the time beside each is its last read.
          </p>
        </header>

        {!set ? (
          <Alert tone="error" title="The list of outlets cannot be reached right now.">Try again in a minute.</Alert>
        ) : (
          <>
            <div className="grid gap-2">
              <CoverageBar outlets={mastheads} size="lg" width={300} draw className="lg:!hidden" />
              <CoverageBar outlets={mastheads} size="lg" width={520} draw className="!hidden lg:!inline-flex" />
              <p className="p-count whitespace-normal">
                {set.outlets} outlets · {feeds.length} feeds · {languages} languages{set.checked_at ? ` · checked ${relativeTime(set.checked_at)}` : ""}
              </p>
            </div>

            {ORIGINS.map((origin) => {
              const group = feeds.filter((f) => f.origin === origin);
              const outlets = new Set(group.map((f) => f.publisher)).size;
              return (
                <section key={origin} aria-labelledby={`origin-${origin}`} className="grid grid-cols-[minmax(0,1fr)] gap-1">
                  <SectionHead id={`origin-${origin}`} title={ORIGIN_LABEL[origin]} sub={group.length ? `${plural(outlets, "outlet")} · ${plural(group.length, "feed")}` : "0 outlets"} />
                  {group.length ? (
                    <ul>{group.map((f) => <FeedRow key={f.slug} feed={f} />)}</ul>
                  ) : (
                    <p style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)" }}>None read yet.</p>
                  )}
                </section>
              );
            })}
          </>
        )}

        {missing.length > 0 && (
          <section aria-labelledby="gaps-title" className="grid gap-1">
            <SectionHead id="gaps-title" title="Not read yet" />
            <p className="max-w-[60ch]" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
              Among the most-read Indian languages, Prism has no outlet yet in {missing.map(langName).join(", ")}. A story reported only in these languages is not on the record. More Indian-language outlets are next.
            </p>
          </section>
        )}

        <InShortCard title="Which outlets">
          Prism reads outlets that publish news about India in their own name through a public feed: Indian papers and broadcasters in English and Indian languages, and a few specialist feeds for a professional reading, such as a regulator&rsquo;s own releases. An outlet is described by where it publishes and in which language, never by a rating of its politics or its tone. Several feeds from one masthead count as one outlet.
        </InShortCard>

        <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
          An outlet missing that covered a story? Say so from the foot of that story, or read <Link href="/about#accountability" className="p-link">who answers for Prism</Link>.
        </p>
      </div>
    </>
  );
}
