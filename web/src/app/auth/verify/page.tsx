"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { saveSession, verifyMagicLink } from "@/lib/session";

function Verify() {
  const params = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setError("This sign-in link is missing its token.");
      return;
    }
    let cancelled = false;
    verifyMagicLink(token)
      .then(({ session, needsProfile }) => {
        if (cancelled) return;
        saveSession(session);
        // New readers finish onboarding (name/profession/languages); returning
        // readers land straight in the app.
        router.replace(needsProfile ? "/onboarding" : "/feed");
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Sign-in failed.");
      });
    return () => {
      cancelled = true;
    };
  }, [params, router]);

  if (error) {
    return (
      <div className="text-center">
        <p className="text-[16px] font-medium">Couldn&apos;t sign you in</p>
        <p className="mt-2 text-[14px]" style={{ color: "var(--ink-muted)" }}>
          {error}
        </p>
        <Link
          href="/signin"
          className="mt-6 inline-block rounded-full px-5 py-2.5 text-[14px] font-semibold"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          Request a new link
        </Link>
      </div>
    );
  }

  return (
    <p className="text-[15px] font-mono" style={{ color: "var(--ink-muted)" }}>
      Signing you in…
    </p>
  );
}

export default function VerifyPage() {
  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-[420px] items-center justify-center px-5">
      <Suspense fallback={<p className="font-mono text-[15px]" style={{ color: "var(--ink-muted)" }}>Loading…</p>}>
        <Verify />
      </Suspense>
    </div>
  );
}
