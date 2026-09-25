"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Payments } from "@/components/Payments";
import { PlanCard } from "@/components/PlanCard";
import { SectionHead } from "@/components/SectionHead";
import { ThemeToggle } from "@/components/ThemeToggle";
import { BackBar } from "@/components/ui";
import { CONTACT_EMAIL } from "@/lib/legal";
import { clearSession, useSession } from "@/lib/session";

// The account (Design System v2 · money board, Account): who you are, what you
// pay for, what you have paid, and the door out. The plan is first because it
// is why most people come here; Payments always shows, "No charges yet" before
// the first one.
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

  const link = "p-link inline-flex min-h-[44px] items-center underline underline-offset-[3px]";
  const quiet = "underline underline-offset-[3px]";
  return (
    <>
      <div className="lg:hidden"><BackBar label="You" href="/you" /></div>
      <div className="mx-auto grid w-full max-w-[720px] gap-[26px] px-[var(--gutter)] pb-24 pt-[18px] lg:pb-14 lg:pt-10">
        <div className="grid gap-1">
          <h1 className="text-balance [font:var(--t-display-m)] lg:[font:var(--t-display-l)]" style={{ letterSpacing: "var(--track-display)" }}>Account</h1>
          <p className="p-mono break-all" style={{ fontSize: 11.5, color: "var(--ink-3)" }}>{session.email}</p>
        </div>
        <PlanCard session={session} />
        <Payments session={session} />

        <section aria-labelledby="profile-title" className="grid gap-3">
          <SectionHead id="profile-title" title="Your record" hint="Your state, profession and the subjects you follow shape Today." />
          <div className="flex flex-wrap items-center gap-x-5" style={{ font: "600 14.5px/1 var(--font-read)" }}>
            <Link href="/you" className={link}>Profile</Link>
            <Link href="/watchlist" className={link}>Watchlist</Link>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span style={{ font: "var(--t-label)", color: "var(--ink-2)" }}>Theme</span>
            <ThemeToggle />
          </div>
        </section>

        <div className="grid gap-2 pt-4" style={{ borderTop: "1px solid var(--line)" }}>
          <div>
            <button type="button" onClick={() => { clearSession(); router.replace("/feed"); }} className="p-btn p-btn--secondary">Sign out</button>
          </div>
          <p style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)" }}>
            To delete your account and everything we hold, write to <a href={`mailto:${CONTACT_EMAIL}`} className={quiet} style={{ color: "var(--ink-2)" }}>{CONTACT_EMAIL}</a> from this address — see the <Link href="/privacy" className={quiet} style={{ color: "var(--ink-2)" }}>privacy policy</Link>.
          </p>
          <p className="flex flex-wrap gap-x-4" style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)" }}>
            <Link href="/privacy" className="inline-flex min-h-[44px] items-center underline-offset-[3px] hover:underline">Privacy</Link>
            <Link href="/terms" className="inline-flex min-h-[44px] items-center underline-offset-[3px] hover:underline">Terms</Link>
            <Link href="/refunds" className="inline-flex min-h-[44px] items-center underline-offset-[3px] hover:underline">Refunds</Link>
          </p>
        </div>
      </div>
    </>
  );
}
