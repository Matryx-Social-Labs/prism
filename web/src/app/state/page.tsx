import type { Metadata } from "next";
import Link from "next/link";
import { PageTitle } from "@/components/reading/parts";
import { SectionHead } from "@/components/SectionHead";
import { BackBar } from "@/components/ui";
import { fetchStateHubs, type StateHubCount } from "@/lib/api";
import { STATE_HUBS, type StateHub } from "@/lib/regions";
import { breadcrumbLd, collectionPageLd, followRel, jsonLd, social } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// Every state and union territory with its hub (audit 02, P1-1), by name — a
// list of places, never a ranking. Each prints its 30-day count; a hub under
// the floor is listed, marked and not followed, since it asks not to be indexed.
export const revalidate = 600;

const title = "News by state: one record per story";
const description = "The stories placed in each Indian state and union territory, from monitored Indian outlets: counted over 30 days, with who reported each and who said what.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/state" },
  ...social(title, description, "/state"),
};

const count = (n: number) => `${n} ${n === 1 ? "record" : "records"}`;

function HubList({ id, heading, hubs, counts, floor, days }: { id: string; heading: string; hubs: StateHub[]; counts: Map<string, StateHubCount> | null; floor: number; days: number }) {
  return (
    <section aria-labelledby={id} className="grid gap-1">
      <SectionHead id={id} title={heading} count={hubs.length} />
      <ul className="grid sm:grid-cols-2 sm:gap-x-8">
        {hubs.map((h) => {
          const c = counts?.get(h.code);
          return (
            <li key={h.code} className="flex items-baseline justify-between gap-3 border-b py-2.5" style={{ borderColor: "var(--line)" }}>
              <Link href={`/state/${h.slug}`} rel={followRel(c?.indexable)} className="p-link">{h.name}</Link>
              <span className="grid justify-items-end text-right">
                {c ? (
                  <>
                    <span className="p-meta__prov">{count(c.multi_outlet)}</span>
                    {!c.indexable && <span style={{ font: "400 12.5px/1.4 var(--font-read)", color: "var(--ink-3)" }}>fewer than {floor} records in {days} days</span>}
                  </>
                ) : (
                  <span className="p-meta__prov">— · Not counted yet</span>
                )}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default async function StatesIndex() {
  const hubs = await fetchStateHubs(revalidate).catch(() => null);
  const counts = hubs ? new Map(hubs.states.map((s) => [s.code, s])) : null;
  const floor = hubs?.floor ?? 20;
  const days = hubs?.window_days ?? 30;
  const url = `${SITE_URL}/state`;
  const indexable = STATE_HUBS.filter((h) => counts?.get(h.code)?.indexable);
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: jsonLd(collectionPageLd({ url, name: title, description, items: indexable.map((h) => ({ url: `${SITE_URL}/state/${h.slug}`, name: h.name })) })),
        }}
      />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(breadcrumbLd([{ name: "Prism", url: `${SITE_URL}/` }, { name: "States", url }])) }} />
      <div className="contents lg:hidden">
        <BackBar label="Today" href="/feed" />
      </div>
      <div className="mx-auto grid w-full max-w-[820px] grid-cols-[minmax(0,1fr)] gap-6 px-[var(--gutter)] pb-16 pt-5 lg:pt-10">
        <header className="grid gap-2">
          <PageTitle>News by state</PageTitle>
          <p className="max-w-[60ch] text-pretty" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
            The records placed in each state and union territory. The count beside each is its records from two or more outlets in the last {days} days; it follows the outlets Prism reads with a desk there (<Link href="/sources" className="p-link">the full list</Link>), not how much news the place had.
          </p>
        </header>
        <HubList id="states" heading="States" hubs={STATE_HUBS.filter((h) => h.kind === "State")} counts={counts} floor={floor} days={days} />
        <HubList id="union-territories" heading="Union territories" hubs={STATE_HUBS.filter((h) => h.kind === "Union territory")} counts={counts} floor={floor} days={days} />
      </div>
    </>
  );
}
