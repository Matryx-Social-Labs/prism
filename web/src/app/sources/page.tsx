import type { Metadata } from "next";
import Link from "next/link";
import { OutletIcon } from "@/components/Coverage";
import { fetchSources, type MonitoredFeed } from "@/lib/api";
import { ORIGIN_LABEL, type Origin } from "@/lib/coverage";
import { relativeTime } from "@/lib/dateline";
import { langName, langNative } from "@/lib/languages";
import { stateName } from "@/lib/regions";
import { byLanguage, missingLanguages } from "@/lib/sources";

// The monitored set, in public: every outlet Prism reads, and when each was
// last read. Every count on a record ("2 of 27 monitored outlets") is out of
// this list, and nothing here is operational (no feed address, no error text).
export const revalidate = 300;

export const metadata: Metadata = {
  title: "The outlets Prism reads",
  description: "Every outlet Prism monitors, by language, with when each was last read. Every count on a Prism record is out of this list.",
  alternates: { canonical: "/sources" },
};

const SHELL = "mx-auto w-full max-w-[var(--shell)] px-5 sm:px-8 xl:px-10";

function FeedRow({ feed }: { feed: MonitoredFeed }) {
  const notes = [ORIGIN_LABEL[feed.origin as Origin], feed.state && `${stateName(feed.state) ?? feed.state} desk`, feed.sector && `${feed.sector} only`, feed.official && "Official releases"].filter(Boolean);
  return (
    // State is line form, in words: a feed that has not answered in the last
    // hour sits on a dashed rule and says since when.
    <li className="flex items-center gap-3 py-3" style={{ borderTop: `1px ${feed.reachable ? "solid" : "dashed"} var(${feed.reachable ? "--line" : "--line-strong"})` }}>
      <OutletIcon domain={feed.domain} code={feed.code} name={feed.name} size={26} />
      <span className="min-w-0 flex-1">
        <span className="block text-[15px] font-semibold leading-[1.3]">{feed.name}</span>
        <span className="block text-[13px]" style={{ color: "var(--ink-3)" }}>{notes.join(" · ")}</span>
      </span>
      <span className="shrink-0 text-right font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
        {feed.reachable && feed.checked_at ? `Read ${relativeTime(feed.checked_at)}` : feed.ok_at ? `Not reached since ${relativeTime(feed.ok_at)}` : "Not reached yet"}
      </span>
    </li>
  );
}

export default async function SourcesPage() {
  const set = await fetchSources();
  const groups = set ? byLanguage(set.feeds) : [];
  const missing = set ? missingLanguages(set.feeds) : [];
  return (
    <div className={`${SHELL} pb-24 pt-8 lg:pb-20 lg:pt-12`}>
      <div className="max-w-[var(--reading)]">
        <h1 className="font-record text-[34px] font-bold leading-[1.1] tracking-[-0.015em] sm:text-[42px]">The outlets Prism reads</h1>
        <p className="mt-4 text-[17px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
          Every count on a record is out of this list. When a story says <em>2 of {set?.outlets ?? "N"} monitored outlets</em>, these are the {set?.outlets ?? "outlets"} it means, not everyone who covered it. Prism reads each outlet&rsquo;s public feed every few minutes; the time beside each is its last read.
        </p>
        <p className="mt-4 text-[15px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>
          Prism reads outlets that publish news about India in their own name through a public feed: Indian papers and broadcasters in English and Indian languages, and a few specialist feeds for a professional reading, such as a regulator&rsquo;s own releases. An outlet is described by where it publishes and in which language, never by a rating of its politics or its tone. Several feeds from one masthead count as one outlet.
        </p>
        {set && (
          <p className="mt-5 font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>
            {set.outlets} outlets · {set.feeds.length} feeds · {groups.length} languages{set.checked_at ? ` · checked ${relativeTime(set.checked_at)}` : ""}
          </p>
        )}
      </div>

      {!set ? (
        <p className="card mt-8 max-w-[var(--reading)] text-[15px]" style={{ color: "var(--danger)" }}>The list of outlets cannot be reached right now.</p>
      ) : (
        <div className="mt-8 grid gap-x-12 gap-y-8 lg:grid-cols-2">
          {groups.map(([code, feeds]) => (
            <section key={code} aria-labelledby={`lang-${code}`}>
              <h2 id={`lang-${code}`} className="font-record text-[22px] font-bold leading-[1.2]">
                {langName(code)}{code !== "en" && <bdi className="ml-2 text-[18px] font-normal" style={{ color: "var(--ink-3)" }}>{langNative(code)}</bdi>}
                <span className="ml-2 font-mono text-[12px] font-normal" style={{ color: "var(--ink-3)" }}>{new Set(feeds.map((f) => f.publisher)).size}</span>
              </h2>
              <ul className="mt-2">{feeds.map((f) => <FeedRow key={f.slug} feed={f} />)}</ul>
            </section>
          ))}
        </div>
      )}

      {missing.length > 0 && (
        <section className="mt-12 max-w-[var(--reading)] border-t pt-6" style={{ borderColor: "var(--line)" }} aria-labelledby="gaps-title">
          <h2 id="gaps-title" className="font-record text-[22px] font-bold leading-[1.2]">Not read yet</h2>
          <p className="mt-2 text-[15px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>
            Among the most-read Indian languages, Prism has no outlet yet in {missing.map(langName).join(", ")}. A story reported only in these languages is not on the record. More Indian-language outlets are next.
          </p>
        </section>
      )}

      <p className="mt-10 max-w-[var(--reading)] text-[14.5px] leading-[1.6]" style={{ color: "var(--ink-3)" }}>
        An outlet missing that covered a story? Say so from the foot of that story, or read <Link href="/about#accountability" className="underline underline-offset-4">who answers for Prism</Link>.
      </p>
    </div>
  );
}
