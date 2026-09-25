"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { afterSignIn, takeNext } from "@/lib/next";
import { Suspense, useEffect, useState } from "react";

import { saveSession, verifyMagicLink } from "@/lib/session";

// The API answers one 401 for a link that is unknown, expired or already used
// (common/auth.verify_and_consume), so the page says all three in one honest line
// rather than guess which. A fetch that never arrived consumed nothing: that
// link still works, so it says to open it again.
const WHY = {
  missing: "This link is missing part of itself. Open it again from the email, or ask for a new one.",
  unusable: "This link has expired or has already been used. Each link lasts 15 minutes and signs in once, so an old email can't sign anyone in.",
  offline: "Prism could not be reached. Check your connection and open the link from the email again.",
} as const;

const TITLE = { font: "var(--t-display-m)", letterSpacing: "var(--track-display)" } as const;

function Verify() {
  const params = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<keyof typeof WHY | null>(null);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setError("missing");
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
        if (!cancelled) setError(e instanceof TypeError ? "offline" : "unusable");
      });
    return () => {
      cancelled = true;
    };
  }, [params, router]);

  if (error) {
    const next = params.get("next");
    return (
      <>
        <h1 className="text-balance" style={TITLE}>Couldn&apos;t sign you in</h1>
        <p style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>{WHY[error]}</p>
        <Link href={next ? `/signin?next=${encodeURIComponent(next)}` : "/signin"} className="p-btn p-btn--primary p-btn--lg p-btn--block">
          Request a new link
        </Link>
        <Link href="/feed" className="p-link inline-flex min-h-11 items-center justify-self-start" style={{ font: "600 14.5px/1.3 var(--font-read)" }}>
          Keep reading without an account
        </Link>
      </>
    );
  }

  return <Signing />;
}

/** A thin rule instead of a spinner: an ink segment breathing on a hairline (still under reduced motion). */
function Signing() {
  return (
    <>
      <h1 role="status" className="text-balance" style={TITLE}>Signing you in…</h1>
      <div className="h-0.5 overflow-hidden" style={{ background: "var(--line)" }} aria-hidden>
        <div className="p-skel h-0.5 w-[46%] rounded-none" style={{ background: "var(--ink)" }} />
      </div>
      <p style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)" }}>
        A new reader goes on to set up their feed. A returning one goes back where they were.
      </p>
    </>
  );
}

export default function VerifyPage() {
  return (
    <div className="mx-auto grid w-full max-w-[420px] content-start gap-3.5 px-[var(--gutter)] py-20 lg:px-0 lg:py-[120px]">
      <Suspense fallback={<Signing />}>
        <Verify />
      </Suspense>
    </div>
  );
}
