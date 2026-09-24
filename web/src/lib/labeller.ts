"use client";

// The labeller workspace client (api/routes/labeller.py). Signed-in only: every
// call carries the reader's Bearer session. Starting a batch returns the same
// per-batch credential a founder's invite link carries, and it is stored where
// the task page already looks for one — so from Start onward the task page is
// unchanged.

import { API_URL, type LabelGuide } from "@/lib/api";
import { authHeader, type Session } from "@/lib/session";

export type LabellerStatus = "none" | "applied" | "active" | "paused" | "removed";

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

/** One task kind's standing for this labeller (phase 3). */
export interface LabellerKind {
  kind: string;
  qualified: boolean;
  best_score: number | null;
  attempts: number;
  can_practise: boolean;
  /** False once passed, during the retake wait, or while the test has too few
   *  questions in this labeller's languages. */
  can_test: boolean;
  retake_at: string | null;
  has_work: boolean;
}

export interface LabellerBatches {
  status: LabellerStatus;
  ready: LabellerBatch[];
  done: LabellerBatch[];
  kinds?: LabellerKind[];
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
    // The status travels with the message: the guide page tells "sign in"
    // (401) from "apply first" (403) from "no such task" (404).
    throw Object.assign(new Error(message), { status: res.status });
  }
  return (await res.json()) as T;
}

export const fetchLabellerMe = (s: Session) => call<LabellerMe>(s, "/api/v1/labeller/me");

/** A task's guide, for an account that has applied (api/routes/labeller.read_guide). */
export const fetchGuide = (s: Session, kind: string) =>
  call<LabelGuide>(s, `/api/v1/labeller/guides/${encodeURIComponent(kind)}`);

/** Who may read the guides: anyone who has applied (founder decision G1). */
export const READS_GUIDES: readonly LabellerStatus[] = ["applied", "active", "paused"];

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
export const LEARNABLE: readonly string[] = ["event_identity", "story_boundary", "claim_attribution", "quote_rendering", "topic_relation", "brief_support"];

async function startRound(s: Session, path: string): Promise<string> {
  const { key, token } = await call<{ key: string; token: string }>(s, path, { method: "POST" });
  try {
    window.localStorage.setItem(labelTokenKey(key), token);
  } catch {
    throw new Error("This browser is blocking storage, which labelling needs. Try a normal window.");
  }
  return `/label/${encodeURIComponent(key)}`;
}

/** A practice round: answer, then see the expected answer and why. */
export const startPractice = (s: Session, kind: string) =>
  startRound(s, `/api/v1/labeller/practice/${encodeURIComponent(kind)}/start`);

/** A scored test for one kind: questions drawn at random, 90% to pass. */
export const startTest = (s: Session, kind: string) =>
  startRound(s, `/api/v1/labeller/qualify/${encodeURIComponent(kind)}/start`);

/** What each kind of task asks, in the reader's words. */
export const KIND_QUESTION: Record<string, string> = {
  story_boundary: "Is this the same story?",
  event_identity: "Is this the same happening?",
  topic_relation: "Is this the same topic?",
  claim_attribution: "Who said this?",
  quote_rendering: "Same statement, or a translation?",
  brief_support: "Does the report say this?",
};
