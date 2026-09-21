"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { afterSignIn, takeNext } from "@/lib/next";
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
        router.replace(afterSignIn(needsProfile, takeNext("/feed", params.get("next"))));
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
      <div className="card p-6 text-center">
        <p className="font-record text-[22px] font-bold">Couldn&apos;t sign you in</p>
        <p className="mt-2 text-[14.5px]" style={{ color: "var(--ink-2)" }}>
          {error}
        </p>
        <Link href="/signin" className="btn btn-primary mt-5">
          Request a new link
        </Link>
      </div>
    );
  }

  return (
    <p className="text-[15px]" style={{ color: "var(--ink-2)" }} role="status">
      Signing you in…
    </p>
  );
}

export default function VerifyPage() {
  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-[420px] items-center justify-center px-5">
      <Suspense fallback={<p className="text-[15px]" style={{ color: "var(--ink-2)" }}>Loading…</p>}>
        <Verify />
      </Suspense>
    </div>
  );
}
