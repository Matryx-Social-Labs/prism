// Typed client for the Parse API (mirrors api/main.py response models).
// The React Native app will reuse these types via packages/api-client later.

// typeof guard: Next inlines NEXT_PUBLIC_* at build time, but this module
// is also bundled outside Next (design-system sync) where `process` is gone.
export const API_URL =
  (typeof process !== "undefined" ? process.env.NEXT_PUBLIC_API_URL : undefined)?.replace(
    /\/$/,
    ""
  ) ?? "http://localhost:8000";

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
  is_regional: boolean;
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
  score: number;
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
  url: string | null;
  title: string;
  published_at: string | null;
  stance: string | null;
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
}

export interface ThreadNodeOut {
  event_id: string;
  title: string;
  sector: string | null;
  occurred_at: string | null;
  relation: string;
  rationale: string | null;
  confidence: number | null;
  image_url: string | null;
}

export interface PerspectiveOut {
  label: string;
  stance: string | null;
  origin_country: string | null;
  summary: string | null;
  article_ids: string[];
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
}
export interface StoryTimelineData {
  developments: StoryDevelopment[];
  cast: string[];
}

export interface EventDetail {
  id: string;
  title: string;
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
  thread: { upstream: ThreadNodeOut[]; downstream: ThreadNodeOut[] };
  related: { id: string; title: string; last_updated_at: string; shared: number }[];
  story: StoryTimelineData;
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
}

export interface FeedQuery {
  lens?: string;
  sector?: string;
  interests?: string[];
  region?: string | null;
  state?: string | null;
  languages?: string[];
  sort?: "latest" | "top";
  limit?: number;
}

export interface RegionState {
  code: string;
  name: string;
  covered: boolean;
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

export interface TrendingStory {
  slug: string;
  label: string;
  cast: string[];
  source_count: number;
  velocity: number; // distinct new outlets in the last 6h
  developments: number;
  sector: string | null;
  hero_title: string | null;
  hero_image: string | null;
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

export interface TrendingStoryDetail {
  slug: string;
  canonical_slug: string;
  label: string;
  cast: string[];
  sector: string | null;
  source_count: number;
  velocity: number;
  status: string;
  developments: StoryDevelopment[];
  timeline_cast: string[];
  /** Null for a storyline that predates the current partition run. */
  branches: BranchTreeData | null;
}

export async function fetchTrendingStory(slug: string): Promise<TrendingStoryDetail | null> {
  const res = await fetch(`${API_URL}/api/v1/trending/${encodeURIComponent(slug)}`, {
    next: { revalidate: 120 },
  });
  if (!res.ok) return null;
  return (await res.json()) as TrendingStoryDetail;
}

export interface MarketDigest {
  headline: string;
  narrative: string;
  movers: { ticker: string; note: string }[];
  event_ids: string[];
  generated_at: string | null;
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

export async function fetchEvent(id: string): Promise<EventDetail> {
  const res = await fetch(`${API_URL}/api/v1/events/${encodeURIComponent(id)}`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`event failed: ${res.status}`);
  return (await res.json()) as EventDetail;
}

export async function fetchQuestions(id: string, lens?: string): Promise<string[]> {
  const params = lens ? `?lens=${encodeURIComponent(lens)}` : "";
  const res = await fetch(`${API_URL}/api/v1/events/${encodeURIComponent(id)}/questions${params}`, {
    cache: "no-store",
  });
  if (!res.ok) return [];
  const data = (await res.json()) as { questions: string[] };
  return data.questions;
}

export async function fetchBrief(
  eventId: string,
  lens: string,
): Promise<{ lens: string; brief: string | null; points?: string[]; cached: boolean } | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/events/${encodeURIComponent(eventId)}/brief?lens=${encodeURIComponent(lens)}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export interface AskCitation {
  number: number;
  article_id: string;
  source_name: string;
  url: string | null;
}

export interface AskCallbacks {
  onSession?: (sessionId: string) => void;
  onToken: (text: string) => void;
  onCitations: (citations: AskCitation[]) => void;
  onDone: () => void;
  onError: (message: string) => void;
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
): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/events/${encodeURIComponent(eventId)}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
    signal,
  });
  if (!res.ok || !res.body) {
    callbacks.onError(`Request failed (${res.status})`);
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
        else if (payload.type === "citations") callbacks.onCitations(payload.citations ?? []);
        else if (payload.type === "done") callbacks.onDone();
        else if (payload.type === "error") callbacks.onError(payload.message);
      } catch {
        // ignore malformed SSE fragments
      }
    }
  }
}
