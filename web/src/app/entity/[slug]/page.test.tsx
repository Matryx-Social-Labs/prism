import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { EntityPage, EntityQuote } from "@/lib/api";
import { SITE_URL } from "@/lib/site";

const fetchEntity = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchEntity }));
vi.mock("next/navigation", () => ({ notFound: () => { throw new Error("NEXT_NOT_FOUND"); } }));

import EntityHubPage, { generateMetadata } from "@/app/entity/[slug]/page";

// "What <name> said" (P0-3): the quotes the API checked, printed as the record
// prints them, and handed to answer engines in exactly the words shown.
const METRO = "We will complete the metro line to the airport by next year.";
const WATER = "Every home in the city will have piped water by March.";
const REPORTED = "ಮೆಟ್ರೋ ಕಾಮಗಾರಿ ಮುಂದಿನ ವರ್ಷ ಪೂರ್ಣಗೊಳ್ಳಲಿದೆ";

const quote = (id: string, text: string, over: Partial<EntityQuote> = {}): EntityQuote => ({
  id,
  quote_text: text,
  quote_start: null,
  quote_end: null,
  article_id: `a-${id}`,
  source_name: "Deccan Herald",
  url: `https://dh.test/${id}`,
  published_at: "2026-09-24T06:00:00Z",
  lang: "en",
  speech: "direct",
  event_id: `e-${id}`,
  event_title: `Record ${id}`,
  source_index: 2,
  ...over,
});

const page = (quotes: EntityQuote[], over: Partial<EntityPage> = {}): EntityPage => ({
  entity: { slug: "dk-shivakumar", name: "DK Shivakumar", entity_type: "person", schema_type: "Person", qid: null, aliases: [] },
  record_count: 9,
  indexable: true,
  records: [],
  role: quotes.length ? "Deputy Chief Minister" : null,
  quote_count: quotes.filter((q) => q.speech !== "reported").length,
  reported_count: quotes.filter((q) => q.speech === "reported").length,
  quoted_records: new Set(quotes.map((q) => q.event_id)).size,
  quotes_window: 9,
  quotes,
  ...over,
});

const THREE = [quote("q1", METRO), quote("q2", WATER), quote("q3", REPORTED, { speech: "reported", lang: "kn", source_name: "Prajavani" })];
const params = { params: Promise.resolve({ slug: "dk-shivakumar" }) };
const open = async () => render(await EntityHubPage(params));

/** The page's JSON-LD blocks: the CollectionPage about the entity, then its breadcrumb. */
const blocks = (container: HTMLElement) =>
  [...container.querySelectorAll('script[type="application/ld+json"]')].map((s) => JSON.parse(s.textContent ?? "null"));
/** The entity itself, as the CollectionPage is `about` it. */
const entityGraph = (container: HTMLElement) => blocks(container)[0].about;

beforeEach(() => fetchEntity.mockReset());

describe("/entity/[slug] — what they said", () => {
  it("prints the checked quotes under the stories, a report never styled as a quote", async () => {
    fetchEntity.mockResolvedValue(page(THREE));
    await open();
    expect(screen.getByRole("heading", { name: "What DK Shivakumar said" })).toBeInTheDocument();
    expect(screen.getByText(`“${METRO}”`)).toBeInTheDocument();
    // The article's report of what was said: its words, bare, labelled.
    expect(screen.getByText(REPORTED)).toBeInTheDocument();
    expect(screen.queryByText(`“${REPORTED}”`)).not.toBeInTheDocument();
    expect(screen.getByText("reported", { selector: "span[title]" })).toBeInTheDocument();
    // Provenance in the quote page's own words; [n] is the report's place on its record.
    expect(screen.getAllByText(/^DECCAN HERALD · \[2\] · 24 SEPT \d\d:\d\d IST$/)).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: /Open at the quote/ })[0].getAttribute("href")).toMatch(/^https:\/\/dh\.test\/q1#:~:text=/);
    expect(screen.getByRole("link", { name: /Open at the line/ })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "How it was checked" })[0]).toHaveAttribute("href", "/story/e-q1/quote/q1");
    expect(screen.getByRole("link", { name: "Record q1" })).toHaveAttribute("href", "/story/e-q1");
    // Who they are as the articles put it, and the counts, quotes apart from reports.
    expect(screen.getByText("As the articles put it: Deputy Chief Minister")).toBeInTheDocument();
    expect(screen.getByText("2 quotes")).toBeInTheDocument();
    expect(screen.getByText("1 reported")).toBeInTheDocument();
  });

  it("hands answer engines exactly the quotes the reader sees, and no report as a Quotation", async () => {
    fetchEntity.mockResolvedValue(page(THREE));
    const { container } = await open();
    const ld = entityGraph(container);
    const items = ld.subjectOf.itemListElement.map((li: { item: { "@type": string; text: string; spokenByCharacter: { "@id": string } } }) => li.item);
    const shown = [...container.querySelectorAll("blockquote")].map((b) => b.textContent?.replace(/^“|”$/g, ""));
    expect(items.map((q: { text: string }) => q.text)).toEqual(shown);
    expect(shown).toEqual([METRO, WATER]);
    expect(items.every((q: { "@type": string; spokenByCharacter: { "@id": string } }) => q["@type"] === "Quotation" && q.spokenByCharacter["@id"] === ld["@id"])).toBe(true);
  });

  it("prints k of n when the page holds fewer than it counted, and from which stories", async () => {
    fetchEntity.mockResolvedValue(page(THREE, { quote_count: 40, reported_count: 5, record_count: 700, quotes_window: 60 }));
    await open();
    expect(screen.getByText("3 of 45 · newest first · from the latest 60 stories")).toBeInTheDocument();
  });

  it("has no section, no quote count and no Quotation when nothing was said", async () => {
    fetchEntity.mockResolvedValue(page([]));
    const { container } = await open();
    expect(screen.queryByRole("heading", { name: /said/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/quote/)).not.toBeInTheDocument();
    expect(entityGraph(container).subjectOf).toBeUndefined();
  });
});

// Audit 01 P2-3: the page is a CollectionPage about the actor, the count is
// the page's (never the person's description), and a breadcrumb places it.
describe("/entity/[slug] — structured data", () => {
  const row = (id: string) => ({ id, title: `Record ${id}` }) as unknown as EntityPage["records"][number];

  it("is a CollectionPage about the actor, listing the records, with the count in the page's description", async () => {
    fetchEntity.mockResolvedValue(page([], { records: [row("r1"), row("r2")], entity: { slug: "dk-shivakumar", name: "DK Shivakumar", entity_type: "person", schema_type: "Person", qid: "Q123", aliases: [] } }));
    const { container } = await open();
    const [collection, crumbs] = blocks(container);
    const url = `${SITE_URL}/entity/dk-shivakumar`;
    expect(collection["@type"]).toBe("CollectionPage");
    expect(collection.url).toBe(url);
    expect(collection.description).toBe("9 Prism records name DK Shivakumar.");
    expect(collection.about).toMatchObject({ "@type": "Person", "@id": `${url}#entity`, name: "DK Shivakumar", sameAs: ["https://www.wikidata.org/wiki/Q123"] });
    expect(collection.about.description).toBeUndefined();
    expect(collection.mainEntity["@type"]).toBe("ItemList");
    expect(collection.mainEntity["@context"]).toBeUndefined();
    expect(collection.mainEntity.itemListElement.map((i: { name: string }) => i.name)).toEqual(["Record r1", "Record r2"]);
    expect(crumbs["@type"]).toBe("BreadcrumbList");
    expect(crumbs.itemListElement.map((i: { name: string; item: string }) => [i.name, i.item])).toEqual([["Prism", `${SITE_URL}/`], ["DK Shivakumar", url]]);
  });

  it("lists no records it does not have", async () => {
    fetchEntity.mockResolvedValue(page([]));
    const { container } = await open();
    expect(blocks(container)[0].mainEntity).toMatchObject({ numberOfItems: 0, itemListElement: [] });
  });
});

describe("/entity/[slug] — title and description", () => {
  it("leads with what was said from three quotes", async () => {
    fetchEntity.mockResolvedValue(page(THREE));
    const meta = await generateMetadata(params);
    expect(meta.title).toBe("DK Shivakumar — what was said, and every record");
    expect(meta.description).toBe(
      "2 quotes from DK Shivakumar, word for word, and 1 reported statement, all checked against the article, in 3 Prism records, with every outlet that reported them.",
    );
  });

  it("keeps the records title below three", async () => {
    fetchEntity.mockResolvedValue(page(THREE.slice(0, 2)));
    const meta = await generateMetadata(params);
    expect(meta.title).toBe("DK Shivakumar — every record");
    expect(meta.description).toMatch(/^Every Prism record naming DK Shivakumar: 9 stories/);
  });
});
