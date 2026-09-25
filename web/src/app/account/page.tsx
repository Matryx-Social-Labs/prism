"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Payments } from "@/components/Payments";
import { PlanCard } from "@/components/PlanCard";
import { SectionHead } from "@/components/SectionHead";
import { ThemeToggle } from "@/components/ThemeToggle";
import { CONTACT_EMAIL } from "@/lib/legal";
import { clearSession, useSession } from "@/lib/session";

// The account (ui_kits/plus · Account): who you are, what you pay for, what
// you have paid, and the door out, on the same ruled sections as every other
// page. The plan is first because it is why most people come here; Payments
// appears only once there is a charge to show.
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
  return (
    <div className="mx-auto grid w-full max-w-[720px] gap-7 px-[var(--gutter)] pb-20 pt-8 lg:pt-12">
      <SectionHead id="account-title" as="h1" title="Account" sub={session.email} />
      <PlanCard session={session} />
      <Payments session={session} />

      <section aria-labelledby="profile-title">
        <SectionHead id="profile-title" title="Your record" hint="Your state, profession and the subjects you follow shape Today." />
        <div className="flex flex-wrap items-center gap-x-5" style={{ font: "600 14.5px/1 var(--font-read)" }}>
          <Link href="/you" className={link}>Profile</Link>
          <Link href="/watchlist" className={link}>Watchlist</Link>
          <span className="ml-auto"><ThemeToggle /></span>
        </div>
      </section>

      <div className="grid gap-1 pt-3" style={{ borderTop: "1px solid var(--line)" }}>
        <p className="flex flex-wrap items-center gap-x-1.5" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
          <span>
            To delete your account and everything we hold, write to <a href={`mailto:${CONTACT_EMAIL}`} className="underline underline-offset-[3px]" style={{ color: "var(--ink-2)" }}>{CONTACT_EMAIL}</a> from this address — see the <Link href="/privacy" className="underline underline-offset-[3px]" style={{ color: "var(--ink-2)" }}>privacy policy</Link>.
          </span>
          <button
            type="button"
            onClick={() => { clearSession(); router.replace("/feed"); }}
            className="inline-flex min-h-[44px] items-center font-semibold underline underline-offset-[3px]"
            style={{ color: "var(--ink-2)" }}
          >
            Sign out
          </button>
        </p>
        <p className="flex flex-wrap gap-x-4" style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)" }}>
          <Link href="/privacy" className="inline-flex min-h-[44px] items-center underline-offset-[3px] hover:underline">Privacy</Link>
          <Link href="/terms" className="inline-flex min-h-[44px] items-center underline-offset-[3px] hover:underline">Terms</Link>
          <Link href="/refunds" className="inline-flex min-h-[44px] items-center underline-offset-[3px] hover:underline">Refunds</Link>
        </p>
      </div>
    </div>
  );
}
