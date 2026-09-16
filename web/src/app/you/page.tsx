"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Masthead } from "@/components/Masthead";
import { interestsToPicks, picksToInterests, useTaxonomy, type Picks } from "@/components/ProfileEditor";
import { ProfessionField, SectorsField, StateField, useProfessionGroups } from "@/components/ReservationForm";
import { SectionHead } from "@/components/SectionHead";
import { ThemeToggle } from "@/components/ThemeToggle";
import type { ProfessionOption } from "@/lib/api";
import { shortDate } from "@/lib/dateline";
import { loadProfile, saveProfile } from "@/lib/profile";
import { clearSession, useSession } from "@/lib/session";
import { getWatchlist, watchlistEvents, type WatchEvent, type WatchItem } from "@/lib/watchlist";

/**
 * You (shape brief §8): the reservation form, all four fields at once, then
 * what the reader follows and the account row. Saving re-sorts For you, so
 * Save returns to the chart. The form is the same component onboarding walks
 * through in three steps.
 */
export default function YouPage() {
  const router = useRouter();
  const session = useSession();
  const taxonomy = useTaxonomy();
  const groups = useProfessionGroups();
  const [loaded, setLoaded] = useState(false);
  const [state, setState] = useState("");
  const [lens, setLens] = useState("reader");
  const [profession, setProfession] = useState<string | null>(null);
  const [picks, setPicks] = useState<Picks>({});
  const [follows, setFollows] = useState<WatchItem[]>([]);
  const [recent, setRecent] = useState<WatchEvent[]>([]);

  useEffect(() => {
    const p = loadProfile();
    if (p) {
      setLens(p.lens);
      if (p.state) setState(p.state);
      setPicks(interestsToPicks(p.interests));
    }
    setLoaded(true);
  }, []);

  useEffect(() => {
    if (!session) return;
    getWatchlist(session).then(setFollows).catch(() => setFollows([]));
    watchlistEvents(session).then(setRecent).catch(() => setRecent([]));
  }, [session]);

  // On this page a profession sets the lens and nothing else: the reader's
  // subjects are theirs, and are only pre-set when they have picked none.
  const pickProfession = (p: ProfessionOption) => {
    setProfession(p.slug);
    setLens(p.lens);
    setPicks((cur) => (Object.keys(cur).length ? cur : interestsToPicks(p.interests)));
  };

  const save = () => {
    // English only for now (founder, 2026-09-16): the profile keeps whatever
    // language order it already had, and defaults to English.
    saveProfile({ lens, region: "IN", state: state || null, interests: picksToInterests(picks), languages: loadProfile()?.languages ?? ["en"] });
    router.push("/feed");
  };

  const signOut = () => {
    clearSession();
    window.location.href = "/feed";
  };

  const identity = session ? `Signed in as ${session.email}.` : "Your profile lives in this browser; no account needed.";

  return (
    <div className="mx-auto max-w-[720px] px-5 pb-24 sm:px-8 lg:pb-16">
      <Masthead dateline={null} />
      <h1 className="pt-4 font-display text-[26px] uppercase leading-none tracking-[0.03em]">You</h1>
      <p className="mt-2 text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
        Everything your chart is built from. {identity}
      </p>

      {loaded && (
        <form className="mt-4" onSubmit={(e) => { e.preventDefault(); save(); }}>
          <StateField value={state} onChange={setState} />
          <ProfessionField groups={groups} profession={profession} lens={lens} onPick={pickProfession} />
          <SectorsField taxonomy={taxonomy} picks={picks} onPicks={setPicks} />
          <div className="rule-live flex flex-wrap items-center gap-x-5 gap-y-3 py-6">
            <button type="submit" className="rounded-full px-6 py-3 text-[14.5px] font-semibold transition hover:opacity-85" style={{ background: "var(--ink)", color: "var(--bg)" }}>
              Save and re-sort my chart
            </button>
            <Link href="/feed" className="text-[14px] underline underline-offset-4" style={{ color: "var(--ink-muted)" }}>Cancel</Link>
          </div>
        </form>
      )}

      <section className="mt-6" aria-labelledby="following-title">
        <SectionHead id="following-title" title="Following" count={session ? follows.length : undefined} />
        {session ? (
          <>
            {follows.length > 0 ? (
              <ul className="flex flex-wrap gap-x-4 gap-y-2 font-mono text-[12px]" style={{ color: "var(--ink)" }}>
                {follows.map((w) => <li key={`${w.kind}:${w.value}`}>{w.value}</li>)}
              </ul>
            ) : (
              <p className="text-[14px]" style={{ color: "var(--ink-muted)" }}>Nothing followed yet. Follow tickers and sectors from any story.</p>
            )}
            <Link href="/watchlist" className="mt-3 inline-block font-mono text-[11px] uppercase tracking-[0.06em] underline-offset-4 hover:underline" style={{ color: "var(--ink-muted)" }}>
              Manage the watchlist →
            </Link>
            {recent.length > 0 && (
              <ol className="mt-4">
                {recent.slice(0, 3).map((e) => (
                  <li key={e.id} className="rule-live">
                    <Link href={`/story/${e.id}`} className="block py-3">
                      <p className="text-[15px] font-medium leading-[1.4]">{e.title}</p>
                      <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--ink-faint)" }}>{shortDate(e.last_updated_at)}</p>
                    </Link>
                  </li>
                ))}
              </ol>
            )}
          </>
        ) : (
          <Link href="/signin" className="text-[14.5px] font-medium underline underline-offset-4" style={{ color: "var(--ink)" }}>
            Sign in to follow tickers and sectors →
          </Link>
        )}
      </section>

      <section className="mt-10" aria-labelledby="account-title">
        <SectionHead id="account-title" title="Account" />
        <div className="rule-live flex min-h-[52px] items-center">
          <span className="text-[14.5px]">Theme</span>
          <span className="ml-auto"><ThemeToggle /></span>
        </div>
        {session ? (
          <button onClick={signOut} className="rule-live flex min-h-[52px] w-full items-center text-left text-[14.5px] font-medium" style={{ color: "var(--danger)" }}>
            Sign out
          </button>
        ) : (
          <Link href="/signin" className="rule-live flex min-h-[52px] items-center text-[14.5px] font-medium">Sign in</Link>
        )}
      </section>
    </div>
  );
}
