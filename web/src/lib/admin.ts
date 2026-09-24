"use client";

// The /admin dashboard's client (api/routes/admin*.py). Every call carries the
// founder's Bearer session; the server decides who is an admin
// (PRISM_ADMIN_EMAILS), so nothing here is trusted to hide anything.

import { API_URL } from "@/lib/api";
import { authHeader, type Session } from "@/lib/session";

/** A failed admin call, keeping the status so the shell can tell "sign in"
 *  (401) from "not for this account" (403) from a real error. */
export class AdminError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function adminCall<T>(session: Session, path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeader(session), ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let message = "Something went wrong";
    try {
      message = ((await res.json()) as { detail?: string }).detail ?? message;
    } catch {
      /* keep the generic message */
    }
    throw new AdminError(res.status, message);
  }
  return (await res.json()) as T;
}

export interface AuditEntry {
  actor: string;
  action: string;
  target: string;
  detail: Record<string, unknown>;
  created_at: string;
}

export const fetchAdminMe = (s: Session) => adminCall<{ email: string }>(s, "/api/v1/admin/me");

export const fetchAudit = (s: Session, limit = 100) =>
  adminCall<{ entries: AuditEntry[] }>(s, `/api/v1/admin/audit?limit=${limit}`);

/** An IST date and time, the product's one clock (DESIGN.md, billing dates). */
export function istTime(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Labellers and batches (api/routes/admin_labellers.py) ─────────────────────

export type LabellerStatusAdmin = "applied" | "active" | "paused" | "removed";

export interface AdminLabeller {
  email: string;
  name: string | null;
  status: LabellerStatusAdmin;
  languages_read: string[];
  note: string | null;
  created_at: string;
  approved_at: string | null;
  approved_by: string | null;
  answers: number;
  last_answer_at: string | null;
}

export interface Standing {
  email: string;
  status: LabellerStatusAdmin;
  kind: string;
  passed: boolean;
  best_score: number | null;
  attempts: number;
  granted_by: string | null;
  checks_right: number;
  checks_total: number;
}

export interface AdminBatch {
  key: string;
  name: string;
  kind: string;
  purpose: "work" | "practice" | "qualify";
  open: boolean;
  listed: boolean;
  self_join: boolean;
  created_at: string;
  tasks: number;
  gated: number;
  answered_tasks: number;
  responses: number;
  people: number;
}

export interface RoundItem {
  position: number;
  speaker: string | null;
  quote: string | null;
  answer: string;
  explanation: string;
}

export interface RoundCheck {
  name: string;
  purpose: string;
  items: number;
  missing: number;
  scores: Record<string, number>;
  ok: boolean;
  reasons: string[];
}

const post = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });
const batchPath = (key: string, rest: string) => `/api/v1/admin/batches/${encodeURIComponent(key)}/${rest}`;

export const fetchLabellers = (s: Session) =>
  adminCall<{ labellers: AdminLabeller[]; board: Standing[]; languages: string[] }>(s, "/api/v1/admin/labellers");

export const setLabellerStatus = (s: Session, email: string, status: Exclude<LabellerStatusAdmin, "applied">) =>
  adminCall(s, "/api/v1/admin/labellers/status", post({ email, status }));

export const addLabeller = (s: Session, email: string, languages_read: string[]) =>
  adminCall(s, "/api/v1/admin/labellers/add", post({ email, languages_read }));

export const setQualification = (s: Session, email: string, kind: string, granted: boolean) =>
  adminCall(s, "/api/v1/admin/labellers/qualify", post({ email, kind, granted }));

export const fetchBatches = (s: Session) => adminCall<{ batches: AdminBatch[] }>(s, "/api/v1/admin/batches");

export const setListed = (s: Session, key: string, on: boolean) => adminCall(s, batchPath(key, "listed"), post({ on }));

export const setOpen = (s: Session, key: string, on: boolean) => adminCall(s, batchPath(key, "open"), post({ on }));

export const gateLanguages = (s: Session, key: string) =>
  adminCall<{ gated: Record<string, number> }>(s, batchPath(key, "languages"), { method: "POST" });

export const fetchRound = (s: Session, key: string) =>
  adminCall<{ items: RoundItem[]; check: RoundCheck }>(s, batchPath(key, "items"));

export const saveExplanations = (s: Session, key: string, edits: { position: number; explanation: string }[]) =>
  adminCall<{ saved: number; check: RoundCheck }>(s, batchPath(key, "explanations"), {
    method: "PUT",
    body: JSON.stringify({ edits }),
  });

// ── The product's numbers (api/routes/admin_metrics.py, common/metrics.py) ────

export type MetricUnit = "count" | "inr" | "usd" | "time";

export interface MetricRow {
  key: string;
  label: string;
  /** null: not counted (yet) — never shown as zero. */
  current: number | string | null;
  previous: number | string | null;
  /** One value per IST day of the period; null before counting began. */
  series: Array<number | null> | null;
  /** The period before, day by day, for the dashed line under `series`. */
  prev_series?: Array<number | null> | null;
  unit: MetricUnit;
  source: string;
  note: string | null;
}

export interface SplitRow {
  label: string;
  current: number | null;
  previous: number | null;
}

export interface Breakdown {
  key: string;
  title: string;
  rows: SplitRow[];
  source: string;
  /** Each word's own day-by-day, where the breakdown is drawn stacked. */
  series?: Record<string, Array<number | null>>;
}

export interface MetricSection {
  key: string;
  title: string;
  rows: MetricRow[];
  breakdowns: Breakdown[];
  retention?: { title: string; source: string; rows: { week: string; accounts: number; by_week: Array<number | null> }[] };
  lag?: { title: string; source: string; min_stories: number; rows: { outlet: string; stories: number; first: number; median_hours: number }[] };
}

export interface Metrics {
  range: { days: number; start: string; end: string; prev_start: string; prev_end: string; tz: string };
  counting_since: { usage: string | null; active: string | null };
  sections: MetricSection[];
}

export const fetchMetrics = (s: Session, days: number) => adminCall<Metrics>(s, `/api/v1/admin/metrics?days=${days}`);

/** The weekly CSV. A plain link cannot carry the Bearer session, so fetch it
 *  and hand the browser a file. */
export async function downloadWeeklyCsv(s: Session, weeks = 12): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/admin/metrics/weekly.csv?weeks=${weeks}`, {
    headers: authHeader(s),
    cache: "no-store",
  });
  if (!res.ok) throw new AdminError(res.status, "Could not download the CSV");
  const url = URL.createObjectURL(await res.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: "prism-weekly.csv" });
  a.click();
  URL.revokeObjectURL(url);
}

// ── People, switches, the collection trigger (api/routes/admin_controls.py) ──

export interface Person {
  email: string;
  name: string | null;
  profession: string | null;
  languages: string[];
  state: string | null;
  created_at: string;
  plan: string | null;
  plan_status: string | null;
  provider: string | null;
  active_days: number;
  last_active: string | null;
  labeller: string | null;
}

export interface Flag {
  name: string;
  value: boolean | number;
  does: string;
}

export const fetchPeople = (s: Session) =>
  adminCall<{ total: number; active_window_days: number; people: Person[] }>(s, "/api/v1/admin/people?limit=500");

export const fetchFlags = (s: Session) => adminCall<{ seen_by: string; flags: Flag[] }>(s, "/api/v1/admin/flags");

export const triggerCollection = (s: Session) =>
  adminCall<{ status: string; collecting: boolean }>(s, "/api/v1/admin/pipeline/trigger", { method: "POST" });
