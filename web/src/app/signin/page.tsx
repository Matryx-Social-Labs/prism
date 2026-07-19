"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";

import { requestMagicLink } from "@/lib/session";

export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await requestMagicLink(email.trim(), consent);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-[70vh] w-full max-w-[420px] flex-col justify-center px-5 py-16">
      <h1 className="text-[30px] font-semibold leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        Sign in to Prism
      </h1>
      <p className="mt-2.5 text-[14.5px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
        We&apos;ll email you a one-time link — no password. Your feed and interests
        move to your account.
      </p>

      {sent ? (
        <div
          className="mt-8 rounded-[18px] border px-5 py-6"
          style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
        >
          <p className="text-[15px] font-medium">Check your email.</p>
          <p className="mt-2 text-[13.5px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
            We sent a one-time sign-in link to{" "}
            <span className="font-medium" style={{ color: "var(--ink)" }}>
              {email}
            </span>
            . It expires in 15 minutes.
          </p>
          <p className="mt-3 font-mono text-[11px] leading-[1.5]" style={{ color: "var(--ink-faint)" }}>
            DEV: email delivery isn&apos;t wired yet — the link is printed in the API
            server logs (look for <span style={{ color: "var(--ink-muted)" }}>email_console</span>).
          </p>
        </div>
      ) : (
        <form onSubmit={submit} className="mt-8 flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-[12.5px] font-medium" style={{ color: "var(--ink-muted)" }}>
              Email
            </span>
            <input
              type="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="rounded-[12px] border px-3.5 py-2.5 text-[15px] outline-none"
              style={{ borderColor: "var(--line-strong)", background: "var(--bg)", color: "var(--ink)" }}
            />
          </label>

          <label className="flex items-start gap-2.5 text-[13px] leading-[1.5]" style={{ color: "var(--ink-muted)" }}>
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-0.5 h-4 w-4"
              required
            />
            <span>
              I agree to Prism creating an account for me and processing my email
              per the privacy policy.
            </span>
          </label>

          {error && (
            <p className="text-[13px]" style={{ color: "var(--danger)" }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy || !consent}
            className="mt-1 rounded-full px-5 py-2.5 text-[14px] font-semibold transition-opacity disabled:opacity-45"
            style={{ background: "var(--ink)", color: "var(--bg)" }}
          >
            {busy ? "Sending…" : "Email me a sign-in link"}
          </button>
        </form>
      )}

      <Link href="/feed" className="mt-8 text-[13px]" style={{ color: "var(--ink-faint)" }}>
        ← Keep browsing without an account
      </Link>
    </main>
  );
}
