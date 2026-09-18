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
  "IN-NL": "Nagaland", "IN-OR": "Odisha", "IN-PB": "Punjab", "IN-RJ": "Rajasthan", "IN-SK": "Sikkim",
  "IN-TN": "Tamil Nadu", "IN-TG": "Telangana", "IN-TR": "Tripura", "IN-UP": "Uttar Pradesh", "IN-UT": "Uttarakhand",
  "IN-WB": "West Bengal", "IN-CH": "Chandigarh", "IN-PY": "Puducherry",
};
const COUNTRIES: Record<string, string> = {
  IN: "India", US: "United States", GB: "United Kingdom", CN: "China", PK: "Pakistan", RU: "Russia", IL: "Israel",
  IR: "Iran", UA: "Ukraine", BD: "Bangladesh", LK: "Sri Lanka", NP: "Nepal", AE: "UAE", SA: "Saudi Arabia", JP: "Japan",
  AU: "Australia", CA: "Canada", DE: "Germany", FR: "France", QA: "Qatar", SG: "Singapore",
};

export function regionLabel(regions: string[] | null | undefined): string | null {
  if (!regions?.length) return null;
  const state = regions.find((r) => r in STATES);
  if (state) return STATES[state];
  const country = regions.find((r) => !r.includes("-"));
  if (!country) return null;
  if (country === "IN") return "India";
  return COUNTRIES[country] ?? "World";
}
