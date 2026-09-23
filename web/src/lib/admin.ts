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
