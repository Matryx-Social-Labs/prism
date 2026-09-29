"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { rememberNext, safeNext } from "@/lib/next";
import { type FormEvent, Suspense, useEffect, useState } from "react";

import { Check } from "@/components/icons";
import { Alert, TextField } from "@/components/ui";
import { GoogleSignIn } from "@/components/GoogleSignIn";
import { track } from "@/lib/analytics";
import { ASK_QUESTIONS, LENS_READS } from "@/lib/billing";
import { requestMagicLink } from "@/lib/session";

// Server truths the copy leans on (common/config.py): a link lives 15 minutes
// (prism_magic_token_ttl_min), and a second request for the same address inside
// 30 seconds is silently not sent (prism_magic_request_cooldown_s) — so "Send it
// again" waits those 30 seconds rather than promise a link that never leaves.
const LINK_TTL_MIN = 15;
const RESEND_COOLDOWN_S = 30;

// What an account adds, from the code that enforces it: common/quota.py (via
// ASK_QUESTIONS and LENS_READS), and the watchlist API has no plan gate.
// Without an account the counts are per visit (a browser session), not per day.
const ACCOUNT_ADDS = [
  "A watchlist of tickers and subjects, free",
  `${ASK_QUESTIONS.free} questions a day in Ask, instead of ${ASK_QUESTIONS.anon} a visit without an account`,
  `${LENS_READS.free} professional lens readings a day, instead of ${LENS_READS.anon} a visit without an account`,
];

/** A reader's words for what is wrong with an address, or null when it will do. */
function emailProblem(raw: string): string | null {
  const v = raw.trim();
  if (!v) return "Enter your email address.";
  if (!v.includes("@")) return "That address is missing its @.";
  const [local, domain = ""] = v.split("@");
  if (!local || /\s/.test(v)) return "That address has a space or nothing before the @.";
  if (!/\.[^.\s]{2,}$/.test(domain)) return "That address is missing its ending, like .com or .in.";
  return null;
}

// Slips in a common domain (04 P2-8): suggested beside the field, one tap to
// take, never corrected behind the reader's back — the address may be real.
const DOMAIN_TYPOS: Record<string, string> = {
  "gmial.com": "gmail.com", "gmai.com": "gmail.com", "gmail.co": "gmail.com", "gmail.con": "gmail.com",
  "yahoo.co": "yahoo.com", "hotmial.com": "hotmail.com",
};

/** The address with a mistyped common domain put right, or null when there is nothing to suggest. */
function typoFix(raw: string): string | null {
  const v = raw.trim();
  const at = v.lastIndexOf("@");
  if (at < 1) return null;
  const fix = DOMAIN_TYPOS[v.slice(at + 1).toLowerCase()];
  return fix ? `${v.slice(0, at)}@${fix}` : null;
}

// lib/session's words when the API gave no reason: under the alert's own title they would say it twice.
const NO_REASON = "Could not send the sign-in link";

/** A fetch that never reached the server says so, not "Failed to fetch"; a reason the API gave is shown as given. */
const failure = (err: unknown) => {
  if (err instanceof TypeError) return "Prism could not be reached. Check your connection and try again.";
  if (err instanceof Error && err.message && err.message !== NO_REASON) return err.message;
  return "Prism did not send it. Try again in a minute.";
};

const WAY_OUT = { font: "600 14.5px/1.3 var(--font-read)" } as const;

export default function SignInPage() {
  return (
    <Suspense>
      <SignIn />
    </Suspense>
  );
}

function SignIn() {
  // Where the reader came from, when a gate sent them: the way out goes back
  // there, not to the chart they were not reading.
  const next = safeNext(useSearchParams().get("next"));
  const back = next ?? "/feed";
  const fromStory = back.startsWith("/story/");
  // Remembered for the tab, so Google's callback and a same-tab magic link
  // both finish the trip the reader was on.
  useEffect(() => rememberNext(next), [next]);
  const [email, setEmail] = useState("");
  const [invalid, setInvalid] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function send(): Promise<boolean> {
    setError(null);
    setBusy(true);
    try {
      await requestMagicLink(email.trim(), next);
      // Asked for, not yet used: the gap between the two is the mail that never arrived.
      track("Sign in", { stage: "sent", method: "link" });
      return true;
    } catch (err) {
      setError(failure(err));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const problem = emailProblem(email);
    setInvalid(problem);
    if (problem) return;
    if (await send()) setSent(true);
  }

  const suggestion = typoFix(email);
  const col = "mx-auto grid w-full max-w-[420px] content-start gap-[18px] px-[var(--gutter)] pb-12 pt-7 lg:px-0 lg:pt-[72px]";

  if (sent) {
    return (
      <div className={col}>
        <LinkSent
          email={email.trim()}
          resend={send}
          busy={busy}
          error={error}
          onDifferent={() => {
            setSent(false);
            setError(null);
          }}
        />
        <Link href={back} className="p-link justify-self-start" style={WAY_OUT}>
          {fromStory ? "← Back to the story while you wait" : "Today’s record is open while you wait →"}
        </Link>
      </div>
    );
  }

  return (
    <div className={col}>
      <div>
        {/* A reader a story's gate sent here is almost always new: the page speaks to them. */}
        <h1 className="text-balance" style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>{fromStory ? "Keep reading, free" : "Sign in to Prism"}</h1>
        <p className="mt-2" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
          {fromStory ? "An account is free. We email you a one-time link; no password." : "Enter your email and we’ll send a one-time sign-in link. No password."}
        </p>
      </div>

      {error && <Alert tone="error" title="The link could not be sent">{error}</Alert>}

      <form onSubmit={submit} noValidate className="grid gap-[18px]">
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          autoFocus
          placeholder="you@example.com"
          value={email}
          onChange={(v) => {
            setEmail(v);
            if (invalid) setInvalid(null);
          }}
          error={invalid ?? undefined}
          hint={suggestion ? (
            <>
              Did you mean{" "}
              <button type="button" className="p-link" style={{ overflowWrap: "anywhere" }} onClick={() => setEmail(suggestion)}>{suggestion}</button>?
            </>
          ) : undefined}
        />
        <button type="submit" disabled={busy} aria-busy={busy || undefined} className="p-btn p-btn--primary p-btn--lg p-btn--block">
          {busy ? "Sending…" : "Email me a sign-in link"}
        </button>
      </form>

      {/* The "or" rule and Google's button; nothing at all until the client id is configured. */}
      <GoogleSignIn />

      <p style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)" }}>
        By signing in you agree to the <Link href="/terms" className="underline underline-offset-[3px]">Terms</Link> and the{" "}
        <Link href="/privacy" className="underline underline-offset-[3px]">privacy policy</Link>. The same link comes whether or not you have an account.
      </p>

      <Link href={back} className="p-link inline-flex min-h-11 items-center justify-self-start" style={WAY_OUT}>
        {fromStory ? "← Back to the story, without an account" : "Keep reading without an account"}
      </Link>

      {/* At every width: on a phone this is the only reason given to sign up. */}
      <div className="grid gap-1.5 border-t pt-3.5" style={{ borderColor: "var(--line)" }}>
        <p className="p-field__label">An account adds</p>
        <ul className="grid gap-1.5">
          {ACCOUNT_ADDS.map((x) => (
            <li key={x} className="flex items-center gap-2" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
              <Check size={16} />
              {x}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/** "Check your inbox": where the link went, when it expires, and the two ways on if it has not come. */
function LinkSent({ email, resend, busy, error, onDifferent }: { email: string; resend: () => Promise<boolean>; busy: boolean; error: string | null; onDifferent: () => void }) {
  const [wait, setWait] = useState(RESEND_COOLDOWN_S);
  const [again, setAgain] = useState(false);
  useEffect(() => {
    if (wait <= 0) return;
    const t = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(t);
  }, [wait]);

  async function sendAgain() {
    if (await resend()) {
      setAgain(true);
      setWait(RESEND_COOLDOWN_S);
    }
  }

  return (
    <>
      <p className="p-count">ONE-TIME LINK · EXPIRES IN {LINK_TTL_MIN} MIN</p>
      <h1 className="text-balance" style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>Check your inbox</h1>
      <p role="status" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
        {again ? "Another link is on its way to " : "A link is on its way to "}
        <b style={{ color: "var(--ink)", fontWeight: 600, overflowWrap: "anywhere" }}>{email}</b>. It expires in {LINK_TTL_MIN} minutes.
      </p>
      <div className="p-card grid gap-1.5">
        <p className="p-field__label">Not there after a minute?</p>
        <p style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)" }}>Look in spam or promotions.</p>
        {error && <p className="p-field__error">{error}</p>}
        <div className="mt-1 flex flex-wrap gap-x-4">
          <button type="button" onClick={sendAgain} disabled={busy || wait > 0} className="p-btn p-btn--text px-0">
            {busy ? "Sending…" : "Send it again"}
            {!busy && wait > 0 && <span className="p-mono" style={{ fontSize: 12 }}>{`0:${String(wait).padStart(2, "0")}`}</span>}
          </button>
          <button type="button" onClick={onDifferent} className="p-btn p-btn--text px-0">Use a different email</button>
        </div>
      </div>
    </>
  );
}
