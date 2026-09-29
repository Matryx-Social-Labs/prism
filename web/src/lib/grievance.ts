// The grievance mechanism's client (api/routes/grievances.py): the kinds of
// complaint, the form's address, filing one, and the public monthly report.

import { API_URL } from "@/lib/api";
import { GRIEVANCE_OFFICER } from "@/lib/legal";

/** Exactly the API's list (KINDS); tests/test_grievances.py fails if they differ. The first four are a record's. */
export const GRIEVANCE_KINDS = [
  "A fact is wrong",
  "A quote is not in the article",
  "An outlet says something different",
  "An outlet that covered this is missing",
  "Privacy or my data",
  "Payments or my plan",
  "Something else",
] as const;
export type GrievanceKind = (typeof GRIEVANCE_KINDS)[number];

export const isKind = (v: unknown): v is GrievanceKind => GRIEVANCE_KINDS.includes(v as GrievanceKind);

/** A ?record= worth prefilling: a path on this site, never another site's (`//host`). */
export const recordPath = (v: unknown): string => (typeof v === "string" && v.startsWith("/") && !v.startsWith("//") ? v : "");

/** The form, with the kind and the record already filled in. */
export function grievanceHref(kind: string, record?: string): string {
  const q = new URLSearchParams({ kind });
  if (record) q.set("record", record);
  return `/grievance?${q.toString()}#complain`;
}

export interface GrievanceMonth {
  month: string; // YYYY-MM, IST
  received: number;
  resolved: number;
  rejected: number;
  open: number;
  median_days: number | null;
}
export interface GrievanceReport {
  since: string;
  decide_within_days: number;
  months: GrievanceMonth[]; // newest first, every month since `since`
}

export async function fetchGrievanceReport(): Promise<GrievanceReport | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/grievances/report`, { next: { revalidate: 300 } });
    return res.ok ? ((await res.json()) as GrievanceReport) : null;
  } catch {
    return null;
  }
}

export interface GrievanceInput {
  email: string;
  category: GrievanceKind;
  body: string;
  name: string;
  subject_url: string;
  website: string; // the honeypot
}
export interface FiledGrievance {
  ref: string;
  acknowledged: boolean;
  decide_by: string;
}

const WRITE_INSTEAD = `Write to ${GRIEVANCE_OFFICER.email} instead.`;

/** File a complaint; throws an Error whose message is what to tell the reader. */
export async function fileGrievance(input: GrievanceInput): Promise<FiledGrievance> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1/grievances`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  } catch {
    throw new Error(`Prism could not be reached. ${WRITE_INSTEAD}`);
  }
  if (res.ok) return (await res.json()) as FiledGrievance;
  const detail = await res.json().then((j: { detail?: unknown }) => j.detail, () => null);
  // A 422's detail is a list of field errors; every other refusal is one sentence.
  if (typeof detail === "string") throw new Error(detail);
  if (res.status === 422) throw new Error("Check the email address, and the page if you gave one, then send again.");
  throw new Error(`Your complaint could not be sent. ${WRITE_INSTEAD}`);
}
