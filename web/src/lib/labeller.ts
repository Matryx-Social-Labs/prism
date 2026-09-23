"use client";

// The labeller workspace client (api/routes/labeller.py). Signed-in only: every
// call carries the reader's Bearer session. Starting a batch returns the same
// per-batch credential a founder's invite link carries, and it is stored where
// the task page already looks for one — so from Start onward the task page is
// unchanged.

import { API_URL } from "@/lib/api";
import { authHeader, type Session } from "@/lib/session";

export type LabellerStatus = "none" | "applied" | "active" | "paused";

export interface LanguageChoice {
  code: string;
  name: string;
  native: string;
}

export interface LabellerMe {
  status: LabellerStatus;
  languages_read: string[];
  note: string;
  languages_available: LanguageChoice[];
}

export interface LabellerBatch {
  key: string;
  name: string;
  kind: string;
  notes: string;
  /** Tasks in this batch in the languages this labeller reads. */
  eligible: number;
  /** Of those, how many THIS labeller has answered. */
  answered: number;
  /** How many people have answered anything here — a head count, never their answers. */
  labellers: number;
}

export interface LabellerBatches {
  status: LabellerStatus;
  ready: LabellerBatch[];
  done: LabellerBatch[];
}

/** The key the task page reads its credential from (web/src/app/label/[key]). */
export const labelTokenKey = (batch: string) => `prism.label.token.${batch}`;

async function call<T>(session: Session, path: string, init?: RequestInit): Promise<T> {
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
    throw new Error(message);
  }
  return (await res.json()) as T;
}

export const fetchLabellerMe = (s: Session) => call<LabellerMe>(s, "/api/v1/labeller/me");

export const applyAsLabeller = (s: Session, languages_read: string[], note: string) =>
  call<{ status: LabellerStatus; languages_read: string[] }>(s, "/api/v1/labeller/apply", {
    method: "POST",
    body: JSON.stringify({ languages_read, note }),
  });

export const fetchLabellerBatches = (s: Session) => call<LabellerBatches>(s, "/api/v1/labeller/batches");

/** Mint (or fetch) this account's credential for a batch and store it where the
 *  task page will find it. Returns the batch path to go to. */
export async function startBatch(s: Session, key: string): Promise<string> {
  const { token } = await call<{ token: string }>(s, `/api/v1/labeller/batches/${encodeURIComponent(key)}/start`, {
    method: "POST",
  });
  try {
    window.localStorage.setItem(labelTokenKey(key), token);
  } catch {
    // Storage denied (private mode): the task page would ask them to join
    // anonymously, which is the wrong identity. Fail loudly instead.
    throw new Error("This browser is blocking storage, which labelling needs. Try a normal window.");
  }
  return `/label/${encodeURIComponent(key)}`;
}

/** The kinds with a guide on /label/learn/<kind>. */
export const LEARNABLE: readonly string[] = ["event_identity", "story_boundary", "claim_attribution", "topic_relation"];

/** What each kind of task asks, in the reader's words. */
export const KIND_QUESTION: Record<string, string> = {
  story_boundary: "Is this the same story?",
  event_identity: "Is this the same happening?",
  topic_relation: "Is this the same topic?",
  claim_attribution: "Who said this?",
  quote_rendering: "Same statement, or a translation?",
};
