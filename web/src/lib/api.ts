// Typed client for the Prism API (mirrors api/main.py response models).
// The React Native app will reuse these types via packages/api-client later.

// typeof guard: Next inlines NEXT_PUBLIC_* at build time, but this module
// is also bundled outside Next (design-system sync) where `process` is gone.
export const API_URL =
  (typeof process !== "undefined" ? process.env.NEXT_PUBLIC_API_URL : undefined)?.replace(
    /\/$/,
    ""
  ) ?? "http://localhost:8000";

export interface OutletRef {
  slug: string;
  publisher: string;
  name: string;
  code: string; // monogram, from the source registry
  origin: "national" | "intl" | "regional" | "wire" | string;
  language: string | null;
  domain?: string | null; // the outlet's site, for its favicon
}

export interface FeedItem {
  id: string;
  title: string;
  headline_lang: string | null; // language of `title`; UI tags it when not the reader's primary
  available_languages: string[];
  summary: string | null;
  sector: string | null;
  subsector: string | null;
  regions: string[];
  image_url: string | null;
  /** Whose photograph `image_url` is — the outlet is credited on the thumbnail. */
  image_outlet?: OutletRef | null;
  is_regional: boolean;
  /** Podcast shows with a clip on this story (slugs), at most three. */
  clip_shows?: string[];
  coverage: CoverageOut | null;
  event_type: string | null;
  source_count: number;
  cvss_score: number | null;
  cvss_severity: string | null;
  kev_listed: boolean;
  cve_ids: string[];
  tickers: string[];
  catalyst: string | null;
  price_impact_direction: string | null;
  last_updated_at: string;
  latest_published_at?: string | null;
  score: number;
  /** Every registered source behind the story; the coverage bar and monograms are drawn from it. */
  outlets?: OutletRef[];
}

export interface LensInfo {
  slug: string;
  name: string;
  tagline: string;
}

export interface SourceRef {
  article_id: string;
  source_name: string;
  source_slug: string;
  code?: string | null;
  origin?: string | null;
  language?: string | null;
  publisher?: string | null;
  domain?: string | null;
  /** The report's own lead image; shown only as a credited link preview to that article. */
  image_url?: string | null;
  /** 64-bit perceptual hash of the photo (hex); two uploads of one picture sit a few bits apart. */
  image_phash?: string | null;
  url: string | null;
  title: string;
  published_at: string | null;
  funding: string | null;
}

export interface CoverageOut {
  origins: Record<string, number>;
  unknown: number;
  single_origin: boolean;
}

export interface EntityOut {
  name: string;
  entity_type: string;
  role: string;
  /** The actor's page, where the server has one. Identity is the server's. */
  slug?: string | null;
}

export interface PerspectiveOut {
  label: string;
  origin_country: string | null;
  summary: string | null;
  article_ids: string[];
}

/** One thing somebody said, as the article said it. VERIFIED fields only —
 *  the quote is checked verbatim at write time, the offsets are repaired from
 *  it, source and date come from raw_items. No stance, no said_at: those are
 *  model opinions and a guess must not sit beside a verified quote. */
export interface ClaimOut {
  quote_text: string;
  quote_start: number | null;
  quote_end: number | null;
  /** The article's own words either side of the quote; empty when the span could not be re-verified. */
  context_before?: string;
  context_after?: string;
  article_id: string;
  source_name: string;
  url: string | null;
  published_at: string | null;
  /** The language the ARTICLE printed these words in — never a claim about the
   *  language they were SPOKEN in. An outlet's own translation passes the
   *  verbatim check, because that check asks whether the words are in THIS
   *  ARTICLE. Printing the language is what keeps the card honest. */
  lang?: string | null;
  /** Quotes sharing an utterance are ONE statement printed in two languages;
   *  at most one of them is the words as spoken. Null when alone or unjudged. */
  utterance?: string | null;
  /** The outlet's translation: a confident NO to "spoken in the language
   *  printed?". False means not SHOWN to be one — never "the original". */
  translated?: boolean;
}

export interface SpeakerClaims {
  speaker: string;
  /** Who they are, as the articles put it ("Vice President of the United States"); null when no article said. */
  role?: string | null;
  claims: ClaimOut[];
  /** Every language this speaker is quoted in, in the order `claims` is
   *  interleaved. More than one is the case the card has to label. */
  languages?: string[];
}

export interface ImpactOut {
  id: string;
  entity_name: string | null;
  effect: string;
  direction: string | null;
  horizon: string | null;
  confidence: number | null;
  parent_impact_id: string | null;
}

export interface CyberLens {
  cve_ids?: string[];
  cvss?: { score?: number; vector?: string; severity?: string };
  affected?: { vendor?: string; product?: string; versions?: string }[];
  exploitation?: { known_exploited?: boolean; kev_listed?: boolean; poc_public?: boolean };
  weakness?: string[];
  remediation?: { fix_available?: boolean; action?: string; workaround?: string };
  control_mapping?: { framework: string; control: string; relevance: string }[];
}

export interface FinanceLens {
  tickers?: string[];
  sector?: string;
  catalyst?: string;
  price_impact?: { direction?: string; magnitude?: string; confidence?: number };
}

export interface StoryDevelopment {
  id: string;
  title: string;
  sector: string | null;
  occurred_at: string | null;
  image_url: string | null;
  is_current: boolean;
  why: string | null;
  source_count?: number; // the station's weight on the route map; older payloads omit it
}
export interface StoryTimelineData {
  developments: StoryDevelopment[];
  cast: string[];
}

export interface EventDetail {
  id: string;
  title: string;
  /** "prism" when the headline was written from the reports; null when it is the first report's own. */
  headline_by?: string | null;
  summary: string | null;
  sector: string | null;
  subsector: string | null;
  image_url: string | null;
  regions: string[];
  occurred_at: string | null;
  last_updated_at: string;
  lens_briefs: Record<string, string>;
  lens_points: Record<string, string[]>;
  available_lenses: string[];
  coverage: CoverageOut | null;
  entities: EntityOut[];
  // Reader-tier: evidence, not lens depth. Optional at the type level because
  // the web and the API deploy from two pipelines and /events is cached 60s —
  // a new page can meet an old payload for a window.
  claims?: SpeakerClaims[];
  // No `story` here: /trending/[slug] owns the timeline. See api/schemas.py.
  // What the ticket carries is the way to that owner. Optional: an older
  // payload (two deploy pipelines, 60s cache) simply has no route.
  story_slug?: string | null;
  /** The denominator: outlets Prism monitors, and the collector's last poll.
   *  Optional for the same two-pipeline reason as story_slug. */
  monitored_outlets?: number | null;
  monitored_checked_at?: string | null;
  projection: {
    event_type?: string | null;
    source_count?: number;
    source_slugs?: string[];
    cyber?: CyberLens | null;
    finance?: FinanceLens | null;
  } | null;
  sources: SourceRef[];
  perspectives: PerspectiveOut[];
  impacts: ImpactOut[];
  // Reader-tier evidence: what the news podcasts said about this story. Optional
  // for the same two-pipeline reason as claims; empty until the gate is passed.
  clips?: ClipOut[];
  // Reader-tier signal: what the official accounts said on X, as written. Never
  // in `sources`, never counted. Empty until PRISM_X_ENABLED on the API.
  x_posts?: XPostOut[];
}

/** A post from an official account on X about this story, as written. */
export interface XPostOut {
  post_id: string;
  handle: string;
  name: string;
  tier: string;
  profile_image_url: string | null;
  /** The permalink on X. */
  url: string;
  text: string;
  created_at: string;
  /** url: the post links a report we hold · judge: a model read both. */
  method: string;
  score: number;
}

export interface ClipShow {
  slug: string;
  name: string;
  publisher: string;
  art_url: string | null;
  site_url: string | null;
}

/** A stretch of a podcast episode about this story; the audio is the publisher's own file. */
export interface ClipOut {
  show: ClipShow;
  episode_title: string;
  episode_url: string | null;
  audio_url: string;
  /** The duration WE transcribed; the player reconciles the file it loads against it. */
  audio_duration_s: number | null;
  published_at: string;
  start_s: number;
  end_s: number;
  text: string;
  /** [word, start_s, end_s] for read-along. */
  words: [string, number, number][];
  score: number;
}

export interface FeedQuery {
  lens?: string;
  sector?: string;
  interests?: string[];
  region?: string | null;
  state?: string | null;
  /** all = everything newest first · region = the reader's state · national = India-wide, no state · world = not India. */
  scope?: "all" | "region" | "national" | "world";
  languages?: string[];
  sort?: "latest" | "top";
  limit?: number;
}

export interface RegionState {
  code: string;
  name: string;
  covered: boolean;
}

/** One monitored feed on the public source list (GET /api/v1/sources). */
export interface MonitoredFeed {
  slug: string;
  name: string;
  publisher: string;
  code: string;
  origin: string;
  language: string | null;
  state: string | null;
  sector: string | null;
  domain: string | null;
  official: boolean;
  checked_at: string | null;
  ok_at: string | null;
  reachable: boolean;
}

export interface MonitoredSet {
  /** Distinct publishers: what a story's "k of N monitored outlets" is out of. */
  outlets: number;
  checked_at: string | null;
  feeds: MonitoredFeed[];
}

export async function fetchSources(): Promise<MonitoredSet | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/sources`, { next: { revalidate: 300 } });
    return res.ok ? ((await res.json()) as MonitoredSet) : null;
  } catch {
    return null;
  }
}

export async function fetchRegions(): Promise<RegionState[]> {
  const res = await fetch(`${API_URL}/api/v1/regions`, { next: { revalidate: 3600 } });
  if (!res.ok) return [];
  return ((await res.json()) as { states: RegionState[] }).states;
}

export async function fetchFeed(query: FeedQuery = {}): Promise<FeedItem[]> {
  const params = new URLSearchParams();
  if (query.lens) params.set("lens", query.lens);
  if (query.sector) params.set("sector", query.sector);
  if (query.interests?.length) params.set("interests", query.interests.join(","));
  if (query.region) params.set("region", query.region);
  if (query.state) params.set("state", query.state);
  if (query.scope) params.set("scope", query.scope);
  if (query.languages?.length) params.set("languages", query.languages.join(","));
  if (query.sort) params.set("sort", query.sort);
  if (query.limit) params.set("limit", String(query.limit));
  const res = await fetch(`${API_URL}/api/v1/feed?${params}`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`feed failed: ${res.status}`);
  const data = (await res.json()) as { items: FeedItem[] };
  return data.items;
}

export interface StoryPhoto {
  url: string;
  article_url: string | null;
  outlet: OutletRef | null;
}

export interface TrendingStory {
  slug: string;
  label: string;
  /** Up to four distinct photographs across the story's developments, credited. */
  photos: StoryPhoto[];
  cast: string[];
  source_count: number;
  velocity: number; // distinct new outlets in the last 6h
  developments: number;
  sector: string | null;
  hero_title: string | null;
  hero_image: string | null;
  hero_event_id: string | null; // the ticket a row opens
  first_seen_at: string | null; // SPAN = last_updated_at - first_seen_at
  last_updated_at: string | null; // LAST MOVED
  route: RouteData | null; // the route glyph's data; null when the story predates the partition
  boundary_status?: "provisional" | "verified";
}

export interface RouteNode {
  id: string;
  parent_id: string | null;
  off_spine: boolean;
  occurred_at: string | null;
}

export interface RouteData {
  root_id: string;
  nodes: RouteNode[];
}

export async function fetchTrending(
  opts: { state?: string | null; sector?: string | null; limit?: number } = {},
): Promise<TrendingStory[]> {
  const p = new URLSearchParams();
  if (opts.state) p.set("state", opts.state);
  if (opts.sector) p.set("sector", opts.sector);
  if (opts.limit) p.set("limit", String(opts.limit));
  const res = await fetch(`${API_URL}/api/v1/trending?${p}`, { next: { revalidate: 120 } });
  if (!res.ok) return [];
  return ((await res.json()) as { stories: TrendingStory[] }).stories;
}

/** One node of the L3 branch tree. partition.py has written these columns every
 *  run since the storyline partitioner shipped. */
export interface BranchNode {
  id: string;
  parent_id: string | null;
  off_spine: boolean;
  depth: number;
}

export interface BranchTreeData {
  root_id: string;
  nodes: BranchNode[];
  /** Counted, never inferred — the readout prints these verbatim. */
  shape: { developments: number; branches: number; satellites: number; max_depth: number };
}

export interface StoryOutlet {
  outlet: OutletRef;
  reports: number;
}

export interface TrendingStoryDetail {
  slug: string;
  /** The story's photographs (up to eight, credited) and who reported it, most reports first. */
  photos: StoryPhoto[];
  outlets: StoryOutlet[];
  canonical_slug: string;
  label: string;
  cast: string[];
  cast_refs?: { name: string; slug: string | null }[];
  sector: string | null;
  source_count: number;
  velocity: number;
  status: string;
  developments: StoryDevelopment[];
  timeline_cast: string[];
  /** Null for a storyline that predates the current partition run. */
  branches: BranchTreeData | null;
  /** Different stories that touch this one; never drawn on the route. */
  related: RelatedStory[];
  /** Provisional groups are related coverage, never a chronology. */
  boundary_status?: "provisional" | "verified";
}

export interface RelatedStory {
  slug: string;
  label: string;
  developments: number;
  source_count: number;
  velocity: number;
  last_updated_at: string | null;
  shared_cast: string[];
  causal: boolean;
}

export async function fetchTrendingStory(slug: string): Promise<TrendingStoryDetail | null> {
  const res = await fetch(`${API_URL}/api/v1/trending/${encodeURIComponent(slug)}`, {
    next: { revalidate: 120 },
  });
  if (!res.ok) return null;
  return (await res.json()) as TrendingStoryDetail;
}

export interface SubjectNode {
  path: string;
  slug: string;
  label: string;
  depth: number;
  story_count: number | null;
}

export interface SubjectPage {
  node: SubjectNode;
  ancestors: SubjectNode[];
  children: SubjectNode[];
  story_count: number;
  stories: FeedItem[];
}

export async function fetchSubject(path: string): Promise<SubjectPage | null> {
  const clean = path.split("/").filter(Boolean).map(encodeURIComponent).join("/");
  const res = await fetch(`${API_URL}/api/v1/subject/${clean}`, { next: { revalidate: 120 } });
  if (!res.ok) return null;
  return (await res.json()) as SubjectPage;
}

export interface SubjectTree {
  roots: SubjectNode[];
  nodes: SubjectNode[];
}

export async function fetchSubjects(): Promise<SubjectTree | null> {
  const res = await fetch(`${API_URL}/api/v1/subjects`, { next: { revalidate: 900 } });
  if (!res.ok) return null;
  return (await res.json()) as SubjectTree;
}

export interface EntityRef {
  slug: string;
  name: string;
  entity_type: string;
  /** The schema.org type the extractor's loose vocabulary maps to; "Thing" when unrecognised. */
  schema_type: string;
  qid: string | null;
  aliases: string[];
}

export interface EntityPage {
  entity: EntityRef;
  record_count: number;
  /** False for a stub: the page renders, but asks not to be indexed. */
  indexable: boolean;
  records: FeedItem[];
}

export async function fetchEntity(slug: string): Promise<EntityPage | null> {
  const res = await fetch(`${API_URL}/api/v1/entity/${encodeURIComponent(slug)}`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) return null;
  return (await res.json()) as EntityPage;
}

export interface MarketDigest {
  headline: string;
  narrative: string;
  movers: { ticker: string; note: string }[];
  event_ids: string[];
  generated_at: string | null;
  /** The stories the digest was written from, as chart rows; empty on an older payload. */
  stories?: FeedItem[];
}

export async function fetchDigest(): Promise<MarketDigest | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/digest/markets`, { next: { revalidate: 900 } });
    if (!res.ok || res.status === 204) return null; // 204 = synthesis unavailable → hide the card
    return (await res.json()) as MarketDigest;
  } catch {
    // A cross-origin 5xx is blocked as a CORS error and rejects the fetch. Return
    // null instead of throwing so /pulse resolves to its empty state rather than
    // hanging forever on "Composing today's market pulse…".
    return null;
  }
}

export async function searchEvents(q: string): Promise<FeedItem[]> {
  const res = await fetch(`${API_URL}/api/v1/search?q=${encodeURIComponent(q)}`, { cache: "no-store" });
  if (!res.ok) return [];
  const data = (await res.json()) as { items: FeedItem[] };
  return data.items;
}

export interface TaxonomySector {
  slug: string;
  name: string;
  subsectors: { slug: string; name: string }[];
}

export async function fetchTaxonomy(): Promise<TaxonomySector[]> {
  const res = await fetch(`${API_URL}/api/v1/taxonomy`, { next: { revalidate: 3600 } });
  if (!res.ok) return [];
  const data = (await res.json()) as { sectors: TaxonomySector[] };
  return data.sectors;
}

export interface ProfessionOption {
  slug: string;
  label: string;
  lens: string; // one of general | cyber | markets
  interests: string[]; // default interest sector slugs
}

export interface ProfessionGroup {
  group: string;
  options: ProfessionOption[];
}

// Mirror of common/professions.py lens + interest mapping. /api/v1/professions
// currently returns only {slug,label}, so onboarding's lens/interest auto-map
// lives here. ponytail: duplicated table — delete once grouped() emits
// lens+interests (fetchProfessions already prefers API-provided values).
const PROFESSION_META: Record<string, { lens: string; interests: string[] }> = {
  trader: { lens: "markets", interests: ["finance"] },
  investor: { lens: "markets", interests: ["finance", "business"] },
  financial_analyst: { lens: "markets", interests: ["finance", "business"] },
  banker: { lens: "markets", interests: ["finance"] },
  wealth_advisor: { lens: "markets", interests: ["finance"] },
  accountant: { lens: "markets", interests: ["finance", "business"] },
  security_analyst: { lens: "cyber", interests: ["cybersecurity"] },
  ciso: { lens: "cyber", interests: ["cybersecurity"] },
  grc: { lens: "cyber", interests: ["cybersecurity"] },
  it_admin: { lens: "cyber", interests: ["cybersecurity", "technology"] },
  pentester: { lens: "cyber", interests: ["cybersecurity"] },
  devsecops: { lens: "cyber", interests: ["cybersecurity", "technology"] },
  software_engineer: { lens: "reader", interests: ["technology"] },
  product_manager: { lens: "reader", interests: ["technology", "business"] },
  data_scientist: { lens: "reader", interests: ["technology"] },
  designer: { lens: "reader", interests: ["technology"] },
  tech_founder: { lens: "reader", interests: ["technology", "business", "finance"] },
  policy_analyst: { lens: "reader", interests: ["politics"] },
  civil_servant: { lens: "reader", interests: ["politics"] },
  lawyer: { lens: "reader", interests: ["politics", "business"] },
  journalist: { lens: "reader", interests: ["politics", "business"] },
  diplomat: { lens: "reader", interests: ["politics"] },
  executive: { lens: "markets", interests: ["business", "finance"] },
  consultant: { lens: "reader", interests: ["business", "finance"] },
  entrepreneur: { lens: "reader", interests: ["business", "finance"] },
  marketer: { lens: "reader", interests: ["business"] },
  operations: { lens: "reader", interests: ["business"] },
  healthcare: { lens: "reader", interests: ["health"] },
  researcher: { lens: "reader", interests: ["science"] },
  pharma_biotech: { lens: "reader", interests: ["health", "science", "business"] },
  student: { lens: "reader", interests: [] },
  educator: { lens: "reader", interests: [] },
  other: { lens: "reader", interests: [] },
};

/** Grouped profession vocabulary for onboarding, enriched with lens + interests. */
export async function fetchProfessions(): Promise<ProfessionGroup[]> {
  const res = await fetch(`${API_URL}/api/v1/professions`, { next: { revalidate: 3600 } });
  if (!res.ok) return [];
  const data = (await res.json()) as {
    groups: { group: string; options: { slug: string; label: string; lens?: string; interests?: string[] }[] }[];
  };
  return data.groups.map((g) => ({
    group: g.group,
    options: g.options.map((o) => ({
      slug: o.slug,
      label: o.label,
      lens: o.lens ?? PROFESSION_META[o.slug]?.lens ?? "reader",
      interests: o.interests ?? PROFESSION_META[o.slug]?.interests ?? [],
    })),
  }));
}

export async function fetchLenses(): Promise<LensInfo[]> {
  const res = await fetch(`${API_URL}/api/v1/lenses`, { next: { revalidate: 3600 } });
  if (!res.ok) return [];
  const data = (await res.json()) as { lenses: LensInfo[] };
  return data.lenses;
}

/** What a brief request can come back as.
 *
 *  A discriminated union rather than `T | null`, because the paywall has three
 *  distinct "no brief" outcomes and the reader needs a different affordance for
 *  each: sign in, buy more, or come back later. Collapsing them to null is what
 *  made the first version render an empty panel for all three.
 */
export type BriefResult =
  | { state: "ok"; lens: string; brief: string | null; points?: string[]; cached: boolean }
  | { state: "signin_required" }
  | { state: "no_samples"; remaining: number | null }
  | { state: "unavailable" };

/** Bearer header, or nothing. Kept in one place so no caller invents its own. */
export function authHeaders(token?: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchEvent(id: string, token?: string | null): Promise<EventDetail> {
  const res = await fetch(`${API_URL}/api/v1/events/${encodeURIComponent(id)}`, {
    // CACHING IS CONDITIONAL ON IDENTITY. The payload now carries only the
    // lenses this reader has unlocked, so a shared 60-second cache would serve
    // one reader's paid lens to everyone behind the same cache entry — the
    // paywall leaking through the CDN instead of through the route. Signed-in
    // requests are never shared; anonymous ones are identical for everyone and
    // keep the cache.
    ...(token ? { cache: "no-store" as const } : { next: { revalidate: 60 } }),
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`event failed: ${res.status}`);
  return (await res.json()) as EventDetail;
}

export async function fetchQuestions(
  id: string,
  lens?: string,
  token?: string | null,
): Promise<string[]> {
  const params = lens ? `?lens=${encodeURIComponent(lens)}` : "";
  const res = await fetch(`${API_URL}/api/v1/events/${encodeURIComponent(id)}/questions${params}`, {
    // The one data-derived question (cyber KEV) is served only to a reader who
    // unlocked that lens, so the token has to come along or the paying reader
    // gets the free copy. Already `no-store`, so unlike fetchEvent there is no
    // shared cache entry for identity to poison.
    cache: "no-store",
    headers: authHeaders(token),
  });
  if (!res.ok) return [];
  const data = (await res.json()) as { questions: string[] };
  return data.questions;
}

export async function fetchBrief(
  eventId: string,
  lens: string,
  token?: string | null,
): Promise<BriefResult> {
  try {
    const res = await fetch(`${API_URL}/api/v1/events/${encodeURIComponent(eventId)}/brief?lens=${encodeURIComponent(lens)}`, {
      cache: "no-store",
      headers: authHeaders(token),
    });
    // 401 and 402 ARE THE PRODUCT, not failures. The previous `if (!res.ok)
    // return null` collapsed them into "no brief", so a reader who needed to
    // sign in, and one who had run out of samples, both saw an empty panel with
    // no way forward. The paywall would have been invisible.
    if (res.status === 401) return { state: "signin_required" };
    if (res.status === 402) {
      const body = await res.json().catch(() => ({}));
      const d = body?.detail ?? {};
      // `remaining: null` means NO QUOTA ROW — never granted — which reads
      // differently to the user than "you have spent them all".
      return { state: "no_samples", remaining: d.remaining ?? null };
    }
    if (!res.ok) return { state: "unavailable" };
    return { state: "ok", ...(await res.json()) };
  } catch {
    return { state: "unavailable" };
  }
}

export interface AskCitation {
  number: number;
  /** Every chunk number the answer used from this article; `number` is the first. */
  numbers?: number[];
  article_id: string;
  source_name: string;
  url: string | null;
}

/** Why a question was refused before any retrieval (api/routes/events.py ask). */
export interface AskLimit {
  status: number;
  error?: string;
  used?: number;
  limit?: number;
  signin_helps?: boolean;
  plus_helps?: boolean;
  retry_after_s?: number;
}

/** The shape after the prose (agent/structure.py): one table at most, the
 * honesty line, follow-ups the sources can answer. Row cells are text; `n`
 * is the row's citation marks, rendered with the prose's chip. */
export interface AskStructure {
  kind: "timeline" | "who_said" | "compare" | "numbers" | null;
  columns: string[];
  rows: { a: string; b: string; n: string }[];
  gaps: string | null;
  followups: string[];
}

export interface AskCallbacks {
  onSession?: (sessionId: string) => void;
  onToken: (text: string) => void;
  onStructure?: (structure: AskStructure) => void;
  onCitations: (citations: AskCitation[]) => void;
  onDone: () => void;
  /** `limit` is set when the server said no (429/503) and says what would help. */
  onError: (message: string, limit?: AskLimit) => void;
}

/** POST /ask and consume the SSE stream. */
export async function askQuestion(
  eventId: string,
  question: string,
  sessionId: string | null,
  callbacks: AskCallbacks,
  // Without this, navigating away mid-answer leaves the read loop consuming the
  // stream: connection held open on metered mobile data, setState on a dead
  // component, and the server generating tokens nobody will ever read.
  signal?: AbortSignal,
  token?: string | null,
): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/events/${encodeURIComponent(eventId)}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify({ question, session_id: sessionId }),
    signal,
  });
  if (!res.ok || !res.body) {
    // A 429/503 carries a JSON `detail` naming the way forward (sign in, Plus,
    // wait a minute). Surface it; a bare status code reads as an outage.
    let detail: Record<string, unknown> | null = null;
    try {
      const body = await res.json();
      detail = body && typeof body.detail === "object" ? (body.detail as Record<string, unknown>) : null;
    } catch {
      detail = null;
    }
    if (detail && (res.status === 429 || res.status === 503)) {
      callbacks.onError(String(detail.error ?? "question limit reached"), { status: res.status, ...detail } as AskLimit);
    } else {
      callbacks.onError(`Request failed (${res.status})`);
    }
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    if (signal?.aborted) {
      await reader.cancel().catch(() => {});
      return;
    }
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const dataLine = rawEvent.split("\n").find((l) => l.startsWith("data: "));
      if (!dataLine) continue;
      try {
        const payload = JSON.parse(dataLine.slice(6));
        if (payload.session_id) callbacks.onSession?.(payload.session_id);
        else if (payload.type === "token") callbacks.onToken(payload.text);
        else if (payload.type === "structure") callbacks.onStructure?.(payload as AskStructure);
        else if (payload.type === "citations") callbacks.onCitations(payload.citations ?? []);
        else if (payload.type === "done") callbacks.onDone();
        else if (payload.type === "error") callbacks.onError(payload.message);
      } catch {
        // ignore malformed SSE fragments
      }
    }
  }
}

// ── Labelling (gold-set collection) ─────────────────────────────────────────
// Mirrors api/routes/label.py. The gold set is what every story-layer decision
// is measured against; these types are the contract that lets non-developers
// grow it.

export interface LabelEvent {
  id: string;
  title: string;
  at: string | null; // ISO-8601; the client decides how to show it
  source_count: number;
  actors: string[];
  signals: string[]; // which proposer suggested it — provenance, not a verdict
  native_title?: string; // the founding outlet's own headline, in its language
  language?: string;
}

/** A quote and the speaker the extractor attributed it to. The judgement is
 *  whether the ARTICLE really attributes it that way — the one thing the
 *  verbatim check cannot decide, since a real sentence can be put in the wrong
 *  mouth and still match the source text exactly. */
export interface LabelClaim {
  article_id: string;
  title: string;
  source: string;
  speaker: string;
  quote_text: string;
  context_before: string;
  context_after: string;
  target: string | null;
  stance: string | null;
  /** The article's opening sentences. Indian news names an official ONCE, in the
   *  first line, then calls them by role for the rest of the piece — so without
   *  this "the Collector said" cannot be tied to the claimed speaker. Empty when
   *  the quote is near the top and the context already covers it. */
  lead?: string;
  /** The whole article. Measured on a uniform sample: at ANY window width the
   *  speaker is named near the quote only ~75% of the time, because Indian news
   *  names an official once and then uses their role. Behind a disclosure, so the
   *  common case stays a ten-second read and the hard case is still answerable. */
  article_text?: string;
}

/** One quote as a quote_rendering task shows it. */
export interface LabelRenderedQuote {
  speaker: string;
  quote: string;
  /** The language's English name ("Kannada"), and its code for the lang attribute. */
  language: string;
  code: string;
  outlet: string;
}

/** "Same statement in two languages?" or "spoken in the language printed?"
 *  (tools/gold_renderings --push; labeller workspace phase 4). */
export interface LabelRendering {
  kind: "quote_rendering";
  question: "same" | "spoken";
  speaker: string;
  story: string;
  a: LabelRenderedQuote;
  b: LabelRenderedQuote | null;
}

/** "Does the report say this?" — one line of Prism's brief and the report it
 *  was written from (tools/gold_brief_cites; the Phase 2 gate). */
export interface LabelBriefLine {
  kind: "brief_support";
  line: string;
  story: string;
  report: {
    title: string;
    outlet: string;
    /** The language's English name, and its code for the lang attribute. */
    language: string;
    code: string;
    url: string | null;
    /** The passage closest to the line; the whole report sits behind a disclosure. */
    excerpt: string;
    text: string;
  };
}

export interface LabelTask {
  id: string;
  position: number;
  sector?: string | null;
  /** Absent on story tasks, which predate the second kind. */
  kind?: "claim_attribution" | "quote_rendering" | "brief_support";
  seed?: LabelEvent;
  candidates?: LabelEvent[];
  claim?: LabelClaim;
  rendering?: LabelRendering;
  line?: LabelBriefLine;
}

export interface LabelBatch {
  name: string;
  notes: string | null;
  open: boolean;
  self_join: boolean;
  labeller: string; // display name on the invite; may be shared with someone else
  /** Which task shape this batch serves; the page renders one or the other. */
  kind?: string;
  total: number;
  done: number; // THIS invite's count, not everyone's
  /** work, or a practice round / a qualification test (labeller workspace, phase 3). */
  purpose?: "work" | "practice" | "qualify";
}

/** A PRACTICE answer's feedback. A test never returns one until it is over. */
export interface LabelFeedback {
  correct: boolean;
  /** The ids that should have been selected: candidates, or the task's own id for "yes". */
  expected: string[];
  explanation: string;
}

/** A practice round's or a test's result, once every question in it is answered. */
export interface LabelResult {
  right: number;
  total: number;
  score: number;
  passed: boolean;
  pass_mark: number;
  purpose: "practice" | "qualify";
  /** Only the ones missed, and only now that nothing can be changed. */
  missed: { position: number; about: string; explanation: string }[];
}

/**
 * Mint this visitor their own write credential.
 *
 * Called once on first visit, which is what lets a single link be shared with a
 * group while every person still gets a distinct identity. The token is kept in
 * localStorage and sent in the X-Label-Token header (or a POST body) — never in a
 * URL, path or query string alike, since both are recorded in browser history,
 * Referer headers and server access logs.
 */
export async function joinLabelBatch(key: string, name: string): Promise<string> {
  const r = await fetch(`${API_URL}/api/v1/label/${encodeURIComponent(key)}/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!r.ok) throw new Error(String(r.status));
  return (await r.json()).token as string;
}

/** A task's guide (common/label_guides.py). Served by the API only — to an
 *  applicant's account or to a batch's own invite — so none of it ships in the
 *  site's JavaScript (founder, 2026-09-23). Text carries **strong**, *em* and
 *  ==highlight== markup; see components/label/GuideView.Rich. */
export interface GuideExample {
  mark?: "yes" | "no";
  head: string;
  body: string;
  illustration?: boolean;
}
export interface GuideBlock {
  mark?: "yes" | "no";
  label: string;
  lines: string[];
  body: string;
}
export interface LabelGuide {
  kind: string;
  question: string;
  minutes: number;
  in_short: string;
  lede: string[];
  do: string[];
  dont: string[];
  examples_label: string | null;
  examples: GuideExample[];
  decide?: { blocks: GuideBlock[]; closing: string };
  start: string;
  after: string | null;
}

export async function fetchLabelGuide(key: string, token: string): Promise<LabelGuide> {
  const r = await fetch(`${API_URL}/api/v1/label/${encodeURIComponent(key)}/guide`, {
    cache: "no-store",
    headers: { "X-Label-Token": token },
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export async function fetchLabelBatch(key: string, token: string): Promise<LabelBatch> {
  const r = await fetch(`${API_URL}/api/v1/label/${encodeURIComponent(key)}`, {
    cache: "no-store",
    headers: { "X-Label-Token": token },
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export async function fetchLabelTask(
  key: string,
  token: string
): Promise<{ task: LabelTask | null; closed: boolean; result?: LabelResult }> {
  const r = await fetch(`${API_URL}/api/v1/label/${encodeURIComponent(key)}/next`, {
    cache: "no-store",
    headers: { "X-Label-Token": token },
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export async function postLabelAnswer(
  key: string,
  body: {
    task_id: string;
    token: string;
    selected: string[];
    unsure: boolean;
    /** "I cannot read this language" — about the labeller, not about the story. */
    skipped?: boolean;
    ms_spent: number;
  }
): Promise<{ feedback?: LabelFeedback; requalify?: boolean }> {
  const r = await fetch(`${API_URL}/api/v1/label/${encodeURIComponent(key)}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}
