/**
 * The reader's six subjects, and how they map onto the pipeline's ten sectors.
 *
 * The pipeline classifies into politics, business, finance, technology,
 * cybersecurity, sports, health, science, entertainment and other. A reader
 * does not think in ten: "Business & Markets" is one beat, so is "Tech & Cyber".
 * Six fits a phone's width and a desktop rail. The Markets and Cyber LENSES
 * stay separate from all of this — a lens is a way of reading, not a subject.
 *
 * "Other" is 22% of the corpus and is never a heading. Its stories stay
 * reachable through search and the story page; the taxonomy's failure is not
 * shown to readers as a section. (Founder decision D3, 2026-09-15.)
 *
 * Old URLs keep working: /sector/finance maps to the Business & Markets group.
 */

export interface SectorGroup {
  /** URL slug and the key the strip highlights. */
  slug: string;
  /** Station-code style label for the strip on phones. */
  code: string;
  /** Full name for desktop and headings. */
  name: string;
  /** Pipeline sectors this group is the union of — the `?sector=` value, joined. */
  sectors: string[];
}

export const SECTOR_GROUPS: SectorGroup[] = [
  { slug: "politics", code: "POL", name: "Politics", sectors: ["politics"] },
  { slug: "business", code: "BIZ", name: "Business & Markets", sectors: ["business", "finance"] },
  { slug: "sports", code: "SPO", name: "Sports", sectors: ["sports"] },
  { slug: "tech", code: "TEC", name: "Tech & Cyber", sectors: ["technology", "cybersecurity"] },
  { slug: "health", code: "HLT", name: "Health & Science", sectors: ["health", "science"] },
  { slug: "entertainment", code: "ENT", name: "Entertainment", sectors: ["entertainment"] },
];

/**
 * What the nav actually shows: the six sector groups above, plus the two roots
 * of the subject tree that the old ten sectors had no room for.
 *
 * Civic & Safety is a third of the corpus (crime, accidents, community life)
 * and used to be `other`, which D3 never shows as a heading — so a third of
 * the product was unreachable from the nav. Education was landing in three
 * different wrong places. Both are measured above the floor a section needs.
 *
 * The six keep their `/sector/<slug>` addresses, which are indexed; the two
 * new ones live at `/subject/<path>` because that is what they are. One nav,
 * two URL shapes, and no redirect of a page Google already holds.
 */
export interface NavItem {
  key: string;
  code: string;
  name: string;
  href: string;
}

export const NAV_ITEMS: NavItem[] = [
  ...SECTOR_GROUPS.map((g) => ({ key: g.slug, code: g.code, name: g.name, href: `/sector/${g.slug}` })),
  { key: "education", code: "EDU", name: "Education", href: "/subject/education" },
  { key: "civic", code: "CIV", name: "Civic & Safety", href: "/subject/civic" },
];

const BY_SLUG = new Map(SECTOR_GROUPS.map((g) => [g.slug, g]));
const BY_PIPELINE = new Map(SECTOR_GROUPS.flatMap((g) => g.sectors.map((s) => [s, g] as const)));

/** The group for a URL slug — one of the six, or a legacy pipeline slug. `null` for "other" and unknowns. */
export function sectorGroup(slug: string | null | undefined): SectorGroup | null {
  if (!slug) return null;
  return BY_SLUG.get(slug) ?? BY_PIPELINE.get(slug) ?? null;
}

/** The `?sector=` parameter the feed API expects for a group. */
export function sectorParam(group: SectorGroup): string {
  return group.sectors.join(",");
}

/** The code printed on a row for a story's pipeline sector; "" for "other" so nothing is printed. */
export function sectorCode(pipelineSector: string | null | undefined): string {
  return BY_PIPELINE.get(pipelineSector ?? "")?.code ?? "";
}
