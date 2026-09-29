/**
 * A place name for a row that has no subject: the state when the story has
 * one, else the country. Never "Other" (DESIGN.md: six subjects, and a story
 * outside them is named by where it happened).
 */
const STATES: Record<string, string> = {
  "IN-AP": "Andhra Pradesh", "IN-AR": "Arunachal Pradesh", "IN-AS": "Assam", "IN-BR": "Bihar", "IN-CT": "Chhattisgarh",
  "IN-DL": "Delhi", "IN-GA": "Goa", "IN-GJ": "Gujarat", "IN-HR": "Haryana", "IN-HP": "Himachal Pradesh",
  "IN-JK": "Jammu & Kashmir", "IN-JH": "Jharkhand", "IN-KA": "Karnataka", "IN-KL": "Kerala", "IN-LA": "Ladakh",
  "IN-MP": "Madhya Pradesh", "IN-MH": "Maharashtra", "IN-MN": "Manipur", "IN-ML": "Meghalaya", "IN-MZ": "Mizoram",
  "IN-NL": "Nagaland", "IN-OD": "Odisha", "IN-PB": "Punjab", "IN-RJ": "Rajasthan", "IN-SK": "Sikkim",
  // Uttarakhand is IN-UK in ISO 3166-2 and in the API (common/regions.py); IN-UT here named no row.
  "IN-TN": "Tamil Nadu", "IN-TG": "Telangana", "IN-TR": "Tripura", "IN-UP": "Uttar Pradesh", "IN-UK": "Uttarakhand",
  "IN-WB": "West Bengal", "IN-CH": "Chandigarh", "IN-PY": "Puducherry",
};
const UNION_TERRITORIES = new Set(["IN-DL", "IN-JK", "IN-LA", "IN-CH", "IN-PY"]);
const COUNTRIES: Record<string, string> = {
  IN: "India", US: "United States", GB: "United Kingdom", CN: "China", PK: "Pakistan", RU: "Russia", IL: "Israel",
  IR: "Iran", UA: "Ukraine", BD: "Bangladesh", LK: "Sri Lanka", NP: "Nepal", AE: "UAE", SA: "Saudi Arabia", JP: "Japan",
  AU: "Australia", CA: "Canada", DE: "Germany", FR: "France", QA: "Qatar", SG: "Singapore",
};

/** A state's name from its ISO 3166-2 code ("IN-KA" → Karnataka). */
export const stateName = (code: string): string | null => STATES[code] ?? null;

export function regionLabel(regions: string[] | null | undefined): string | null {
  if (!regions?.length) return null;
  const state = regions.find((r) => r in STATES);
  if (state) return STATES[state];
  const country = regions.find((r) => !r.includes("-"));
  if (!country) return null;
  if (country === "IN") return "India";
  return COUNTRIES[country] ?? "World";
}

/**
 * "Jammu & Kashmir" → "jammu-and-kashmir": a state hub's address, /state/<slug>
 * (audit 02, P1-1). The ISO code is data, never the URL. The same rule as the
 * API's common/regions.state_slug, and the slug the entity folder gives the same
 * name — so /entity/karnataka can defer to /state/karnataka.
 */
export const stateSlug = (name: string): string =>
  name.toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export type StateHub = { code: string; name: string; slug: string; kind: "State" | "Union territory" };

/** The 33 hubs, by name: the index lists them this way, never by volume. */
export const STATE_HUBS: StateHub[] = Object.entries(STATES)
  .map(([code, name]) => ({ code, name, slug: stateSlug(name), kind: UNION_TERRITORIES.has(code) ? ("Union territory" as const) : ("State" as const) }))
  .sort((a, b) => a.name.localeCompare(b.name));

const BY_SLUG = new Map(STATE_HUBS.map((s) => [s.slug, s]));
const BY_CODE = new Map(STATE_HUBS.map((s) => [s.code, s]));

export const stateBySlug = (slug: string): StateHub | null => BY_SLUG.get(slug) ?? null;
export const stateByCode = (code: string): StateHub | null => BY_CODE.get(code) ?? null;
