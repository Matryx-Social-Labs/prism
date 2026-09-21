"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Payments } from "@/components/Payments";
import { PlanCard } from "@/components/PlanCard";
import { SectionHead } from "@/components/SectionHead";
import { ThemeToggle } from "@/components/ThemeToggle";
import { clearSession, useSession } from "@/lib/session";

// The account: who you are, what you pay for, what you have paid, and the
// door out — the same hairline sections as every other page (DESIGN.md
// § Account). The plan is first because it is why most people come here;
// Payments appears only once there is a charge to show.
export default function AccountPage() {
  const session = useSession();
  const router = useRouter();

  useEffect(() => {
    if (session === null && typeof window !== "undefined") {
      const t = setTimeout(() => {
        if (!localStorage.getItem("prism.session.v1")) router.replace("/signin?next=/account");
      }, 0);
      return () => clearTimeout(t);
    }
  }, [session, router]);

  if (!session) return null;

  return (
    <div className="mx-auto w-full max-w-[var(--reading)] px-5 pb-20 pt-8 sm:px-8">
      <h1 className="font-record text-[32px] font-bold leading-[1.1] tracking-[-0.015em]">Account</h1>
      <p className="mt-1.5 font-mono text-[12.5px]" style={{ color: "var(--ink-3)" }}>{session.email}</p>

      <section className="mt-8" aria-labelledby="plan-title">
        <SectionHead id="plan-title" title="Your plan" />
        <PlanCard session={session} />
      </section>
      <Payments session={session} />

      <section className="mt-8" aria-labelledby="profile-title">
        <SectionHead id="profile-title" title="Your record" hint="Your state, profession and the subjects you follow shape Today." />
        <div className="card divide-y p-0" style={{ borderColor: "var(--line)" }}>
          <Link href="/you" className="flex min-h-[56px] items-center px-4 text-[15px] font-medium" style={{ borderColor: "var(--line)" }}>Profile, state and subjects →</Link>
          <Link href="/watchlist" className="flex min-h-[56px] items-center px-4 text-[15px] font-medium" style={{ borderColor: "var(--line)" }}>Watchlist →</Link>
          <div className="flex min-h-[56px] items-center px-4" style={{ borderColor: "var(--line)" }}>
            <span className="text-[15px]">Theme</span>
            <span className="ml-auto"><ThemeToggle /></span>
          </div>
        </div>
      </section>

      <section className="mt-8" aria-labelledby="signout-title">
        <SectionHead id="signout-title" title="Sign out" />
        <div className="card divide-y p-0" style={{ borderColor: "var(--line)" }}>
          <button
            onClick={() => { clearSession(); router.replace("/feed"); }}
            className="flex min-h-[56px] w-full items-center px-4 text-left text-[15px] font-semibold"
            style={{ color: "var(--danger)" }}
          >
            Sign out of Prism
          </button>
        </div>
        <p className="mt-3 text-[13px] leading-[1.5]" style={{ color: "var(--ink-3)" }}>
          To delete your account and everything we hold, write to us from this address — see the <Link href="/privacy" className="underline underline-offset-[3px]">privacy policy</Link>.
        </p>
      </section>

      <p className="mt-8 flex flex-wrap gap-x-4 gap-y-1 text-[13px]" style={{ color: "var(--ink-3)" }}>
        <Link href="/privacy" className="underline-offset-[3px] hover:underline">Privacy</Link>
        <Link href="/terms" className="underline-offset-[3px] hover:underline">Terms</Link>
        <Link href="/refunds" className="underline-offset-[3px] hover:underline">Refunds</Link>
      </p>
    </div>
  );
}
