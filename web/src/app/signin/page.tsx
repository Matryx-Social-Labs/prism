"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { type FormEvent, Suspense, useState } from "react";

import { requestMagicLink } from "@/lib/session";

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
  const next = useSearchParams().get("next");
  const back = next && next.startsWith("/") ? next : "/feed";
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
      <h1 className="text-[30px] font-medium leading-[1.15] text-balance">Sign in to Prism</h1>
      <p className="mt-2.5 text-[14.5px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
        Enter your email and we&apos;ll send a one-time sign-in link. No password.
        New here? You&apos;ll set up your chart right after.
      </p>

      {sent ? (
        <div className="rule-live mt-8 border-b py-6" style={{ borderBottomColor: "var(--line)" }}>
          <p className="text-[15px] font-medium">Check your inbox.</p>
          <p className="mt-2 text-[13.5px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
            If you have an account or want one, a sign-in link is on its way to{" "}
            <span className="font-mono" style={{ color: "var(--ink)" }}>{email}</span>
            . It expires in 15 minutes.
          </p>
        </div>
      ) : (
        <form onSubmit={submit} className="mt-8 flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-[13.5px] font-medium" style={{ color: "var(--ink)" }}>Email</span>
            <input
              type="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="h-12 border px-4 text-[16px] outline-none"
              style={{ borderColor: "var(--line-strong)", background: "var(--bg-elevated)", color: "var(--ink)" }}
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

      <Link href={back} className="mt-8 text-[13.5px] underline underline-offset-4" style={{ color: "var(--ink-muted)" }}>
        {back.startsWith("/story/") ? "Back to the story, without an account" : "Keep reading without an account"}
      </Link>
    </div>
  );
}
