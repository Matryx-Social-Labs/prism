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
    <div className="mx-auto flex min-h-[60dvh] w-full max-w-[440px] flex-col justify-center px-5 py-14">
      <div className="card p-6">
        <h1 className="font-record text-[28px] font-medium leading-[1.15]">Account</h1>
        <dl className="mt-5 border-t pt-4" style={{ borderColor: "var(--line)" }}>
          <dt className="field-label" style={{ color: "var(--ink-3)" }}>Signed in as</dt>
          <dd className="mt-1 font-mono text-[14.5px]" style={{ color: "var(--ink)" }}>{session.email}</dd>
        </dl>
        <div className="mt-6 flex flex-wrap gap-2">
          <button
            onClick={() => {
              clearSession();
              router.replace("/feed");
            }}
            className="btn btn-secondary"
          >
            Sign out
          </button>
          <Link href="/you" className="btn btn-ghost">Your profile</Link>
        </div>
      </div>
      <Link href="/feed" className="mt-6 self-center text-[14px] font-medium underline-offset-4 hover:underline" style={{ color: "var(--ink-2)" }}>
        Back to today&rsquo;s record
      </Link>
    </div>
  );
}
