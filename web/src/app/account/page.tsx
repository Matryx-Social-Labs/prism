"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { clearSession, useSession } from "@/lib/session";

export default function AccountPage() {
  const session = useSession();
  const router = useRouter();

  // Not signed in → send to the sign-in page.
  useEffect(() => {
    if (session === null && typeof window !== "undefined") {
      // useSession initializes to null then syncs; only redirect once we've had
      // a tick to read localStorage. A microtask defer avoids a flash-redirect.
      const t = setTimeout(() => {
        if (!localStorage.getItem("prism.session.v1")) router.replace("/signin");
      }, 0);
      return () => clearTimeout(t);
    }
  }, [session, router]);

  if (!session) return null;

  return (
    <div className="mx-auto flex min-h-[60vh] w-full max-w-[420px] flex-col justify-center px-5 py-16">
      <h1 className="text-[28px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
        Your account
      </h1>
      <dl className="mt-6 rounded-[18px] border px-5 py-4" style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}>
        <dt className="text-[12px] font-medium" style={{ color: "var(--ink-muted)" }}>
          Signed in as
        </dt>
        <dd className="mt-1 font-mono text-[14.5px]" style={{ color: "var(--ink)" }}>
          {session.email}
        </dd>
      </dl>
      <button
        onClick={() => {
          clearSession();
          router.replace("/feed");
        }}
        className="mt-6 self-start rounded-full border px-5 py-2.5 text-[14px] font-semibold"
        style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}
      >
        Sign out
      </button>
      <Link href="/feed" className="mt-6 text-[13px]" style={{ color: "var(--ink-faint)" }}>
        ← Back to your feed
      </Link>
    </div>
  );
}
