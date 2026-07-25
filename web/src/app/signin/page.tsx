"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";

import { requestMagicLink } from "@/lib/session";

export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await requestMagicLink(email.trim());
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-[420px] flex-col justify-center px-5 py-16">
      <h1 className="text-[30px] font-semibold leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        Sign in to Parse
      </h1>
      <p className="mt-2.5 text-[14.5px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
        Enter your email and we&apos;ll send a one-time sign-in link — no password.
        New here? You&apos;ll set up your feed right after.
      </p>

      {sent ? (
        <div
          className="mt-8 rounded-[18px] border px-5 py-6"
          style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
        >
          <p className="text-[15px] font-medium">Check your inbox.</p>
          <p className="mt-2 text-[13.5px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
            If you have an account or want one, a sign-in link is on its way to{" "}
            <span className="font-medium" style={{ fontFamily: "var(--font-mono), monospace", color: "var(--ink)" }}>
              {email}
            </span>
            . It expires in 15 minutes.
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
              className="rounded-[12px] border px-3.5 py-3 text-[16px] outline-none"
              style={{ borderColor: "var(--line-strong)", background: "var(--bg)", color: "var(--ink)" }}
            />
          </label>

          {error && (
            <p className="text-[13px]" style={{ color: "var(--danger)" }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy || !email.trim()}
            className="mt-1 rounded-full px-5 py-3 text-[14px] font-semibold transition-opacity disabled:opacity-45"
            style={{ background: "var(--ink)", color: "var(--bg)" }}
          >
            {busy ? "Sending…" : "Email me a sign-in link"}
          </button>
        </form>
      )}

      <Link href="/feed" className="mt-8 text-[13px]" style={{ color: "var(--ink-faint)" }}>
        ← Keep browsing without an account
      </Link>
    </div>
  );
}
