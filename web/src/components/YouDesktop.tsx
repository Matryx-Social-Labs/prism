"use client";

import Link from "next/link";

import { ThemeToggle } from "@/components/ThemeToggle";
import { langNative } from "@/lib/languages";

// The desktop You screen (Prism Desktop.dc.html, YOU screen) — "How your Prism
// is made", read as a colophon: one ruled ledger of what the reader has set,
// with the EDIT affordance evicted into the 104px mono rail so the values
// themselves stay prose. Same Stone grid as the desktop Feed and Trending.
//
// Below lg this renders nothing and the phone's card stack stands.
//
// DROPPED from the design — no data exists for it:
//  - "Your reading record": twelve weeks of daily marks inked by lens, and the
//    12 WEEKS / 84 DAYS / 61 READ ledger beside it. Prism stores no per-reader
//    reading history (no API, no table); every mark in that block would have
//    been invented. It is the one visual centrepiece of this screen, so it
//    should come back the day reading events are actually recorded.

const RAIL = "grid grid-cols-[104px_1240px] gap-x-8";
const MONO = "font-mono text-[10.5px] uppercase tracking-[0.08em]";

type Props = {
  email: string | null;
  lensName: string;
  stateName: string | null;
  /** ISO 639-1 codes in the reader's preference order. */
  languages: string[];
  /** Already resolved through the taxonomy by the page. */
  interests: string[];
  /** Watchlist values (tickers, sectors); empty when signed out. */
  follows: string[];
  onSignOut: () => void;
};

function Row({
  edit,
  label,
  children,
  muted,
}: {
  edit?: string;
  label: string;
  children: React.ReactNode;
  muted?: boolean;
}) {
  return (
    <div className={`${RAIL} items-baseline`}>
      {edit ? (
        <Link href={edit} className={`${MONO} pt-6 transition hover:opacity-70`} style={{ color: "var(--ink-faint)" }}>
          Edit
        </Link>
      ) : (
        <div />
      )}
      <div
        className="grid max-w-[922px] grid-cols-[254px_1fr] items-baseline gap-x-8 border-b py-[18px]"
        style={{ borderColor: "var(--line)" }}
      >
        <span
          className="text-[12px] font-semibold uppercase tracking-[0.14em]"
          style={{ color: "var(--ink-muted)" }}
        >
          {label}
        </span>
        <span
          className="text-[20px]"
          style={{ fontFamily: "var(--font-display), serif", color: muted ? "var(--ink-faint)" : "var(--ink)" }}
        >
          {children}
        </span>
      </div>
    </div>
  );
}

export function YouDesktop({
  email,
  lensName,
  stateName,
  languages,
  interests,
  follows,
  onSignOut,
}: Props) {
  return (
    <div className="mx-auto hidden w-[1376px] pb-20 lg:block">
      <div className={`${RAIL} pt-6`}>
        <div className={MONO} style={{ color: "var(--ink-faint)" }}>
          Colophon
        </div>
        <div>
          <h1 className="text-[30px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
            How your Prism is made
          </h1>
          <p className="mt-2.5 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
            {email ? (
              `Signed in as ${email} · synced across devices`
            ) : (
              <>
                Browsing without an account · nothing is synced ·{" "}
                <Link href="/signin" className="underline underline-offset-4" style={{ color: "var(--ink)" }}>
                  Sign in
                </Link>
              </>
            )}
          </p>
          <div className="mt-5 border-b" style={{ borderColor: "var(--line)" }} />
        </div>
      </div>

      <div className="pt-2">
        {/* Lens, state, languages and interests are all edited on one page. */}
        <Row edit="/interests" label="Default lens">
          {lensName}
        </Row>
        <Row edit="/interests" label="State" muted={!stateName}>
          {stateName ?? "All India"}
        </Row>
        <Row edit="/interests" label="Languages">
          {languages.map(langNative).join(" · ")}
        </Row>
        <Row edit="/interests" label="Interests" muted={interests.length === 0}>
          {interests.length ? interests.join(" · ") : "Nothing chosen yet"}
        </Row>
        <Row edit={email ? "/watchlist" : "/signin"} label="Watchlist" muted={follows.length === 0}>
          {follows.length
            ? follows.join(" · ")
            : email
              ? "Nothing followed yet"
              : "Sign in to follow tickers and sectors"}
        </Row>
        <Row label="Theme">
          <ThemeToggle />
        </Row>
        {email && (
          <Row label="Account">
            <button onClick={onSignOut} className="text-[20px] transition hover:opacity-70" style={{ color: "var(--danger)" }}>
              Sign out
            </button>
          </Row>
        )}
      </div>
    </div>
  );
}
