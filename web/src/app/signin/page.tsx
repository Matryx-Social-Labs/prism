"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { rememberNext, safeNext } from "@/lib/next";
import { type FormEvent, Suspense, useState, useEffect } from "react";

import { Brand } from "@/components/Brand";
import { requestMagicLink } from "@/lib/session";
import { GoogleSignIn } from "@/components/GoogleSignIn";

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
  // Remembered for the tab, so Google's callback and a same-tab magic link
  // both finish the trip the reader was on.
  useEffect(() => rememberNext(next), [next]);
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await requestMagicLink(email.trim(), next);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-var(--topbar))] w-full max-w-[520px] flex-col justify-center px-5 py-14">
      <div className="mb-6 lg:hidden"><Brand size={26} /></div>
      <div className="border-y py-8 sm:border sm:p-8" style={{ borderColor: "var(--line-strong)", background: "var(--surface)" }}>
        <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em]" style={{ color: "var(--accent)" }}>Reader access</p>
        <h1 className="font-record text-[30px] font-bold leading-[1.25] text-balance">Sign in to Prism</h1>
        <p className="mt-2 text-[15px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>
          Enter your email and we&apos;ll send a one-time sign-in link. No password.
          New here? You&apos;ll set up your record right after.
        </p>

        {sent ? (
          <div className="mt-6 rounded-[var(--r-md)] px-4 py-4" style={{ background: "var(--accent-soft)" }} role="status">
            <p className="text-[15px] font-semibold">Check your inbox.</p>
            <p className="mt-1.5 text-[14px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>
              If you have an account or want one, a sign-in link is on its way to{" "}
              <span className="font-mono" style={{ color: "var(--ink)" }}>{email}</span>
              . It expires in 15 minutes.
            </p>
          </div>
        ) : (
          <form onSubmit={submit} className="mt-6 flex flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="field-label">Email</span>
              <input
                type="email"
                required
                autoFocus
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="input"
              />
            </label>

            {error && (
              <p className="text-[13.5px] font-medium" style={{ color: "var(--danger)" }} role="alert">
                {error}
              </p>
            )}

            <button type="submit" disabled={busy || !email.trim()} className="btn btn-primary btn-lg mt-1">
              {busy ? "Sending…" : "Email me a sign-in link"}
            </button>
            {/* One tap on Android and desktop; hidden until the client id is configured. */}
            <div className="mt-2 flex items-center gap-3" aria-hidden>
              <span className="h-px flex-1" style={{ background: "var(--line)" }} />
              <span className="text-[12.5px]" style={{ color: "var(--ink-3)" }}>or</span>
              <span className="h-px flex-1" style={{ background: "var(--line)" }} />
            </div>
            <GoogleSignIn />
            <p className="mt-4 text-[12.5px] leading-[1.5]" style={{ color: "var(--ink-3)" }}>
              By signing in you agree to the <Link href="/terms" className="underline underline-offset-[3px]">Terms</Link> and the{" "}
              <Link href="/privacy" className="underline underline-offset-[3px]">privacy policy</Link>.
            </p>
          </form>
        )}
      </div>

      <Link href={back} className="mt-6 self-center text-[14px] font-medium underline-offset-4 hover:underline" style={{ color: "var(--ink-2)" }}>
        {back.startsWith("/story/") ? "Back to the story, without an account" : "Keep reading without an account"}
      </Link>
    </div>
  );
}
