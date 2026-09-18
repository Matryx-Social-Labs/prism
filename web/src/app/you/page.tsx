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
import { relativeTime } from "@/lib/dateline";
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
    <div className="mx-auto max-w-[var(--reading)] px-5 pb-[calc(var(--tabbar)+24px)] sm:px-8 lg:max-w-[760px] lg:pb-16">
      <Masthead dateline={null} />
      <div className="lg:pt-6">
        <SectionHead id="you-title" title="You" hint={`Everything your record is built from. ${identity}`} />

        {loaded && (
          <form className="card p-5" onSubmit={(e) => { e.preventDefault(); save(); }}>
            <StateField value={state} onChange={setState} />
            <ProfessionField groups={groups} profession={profession} lens={lens} onPick={pickProfession} />
            <SectorsField taxonomy={taxonomy} picks={picks} onPicks={setPicks} />
            <div className="flex flex-wrap items-center gap-2 border-t pt-5" style={{ borderColor: "var(--line)" }}>
              <button type="submit" className="btn btn-primary">Save and re-sort my record</button>
              <Link href="/feed" className="btn btn-ghost">Cancel</Link>
            </div>
          </form>
        )}

        <section className="mt-8" aria-labelledby="following-title">
          <SectionHead id="following-title" title="Following" count={session ? follows.length : undefined}
            right={session ? <Link href="/watchlist" className="btn btn-secondary btn-sm">Watchlist</Link> : undefined} />
          {session ? (
            <div className="card">
              {follows.length > 0 ? (
                <ul className="flex flex-wrap gap-2">
                  {follows.map((w) => <li key={`${w.kind}:${w.value}`} className="chip h-8 font-mono text-[12px]">{w.value}</li>)}
                </ul>
              ) : (
                <p className="text-[14.5px]" style={{ color: "var(--ink-2)" }}>Nothing followed yet. Follow tickers and sectors from any story.</p>
              )}
              {recent.length > 0 && (
                <ol className="mt-4 flex flex-col divide-y border-t pt-2" style={{ borderColor: "var(--line)" }}>
                  {recent.slice(0, 3).map((e) => (
                    <li key={e.id} style={{ borderColor: "var(--line)" }}>
                      <Link href={`/story/${e.id}`} className="block py-3">
                        <p className="font-record text-[16px] font-medium leading-[1.35]">{e.title}</p>
                        <p className="mt-1 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>{relativeTime(e.last_updated_at)}</p>
                      </Link>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          ) : (
            <div className="card flex flex-wrap items-center justify-between gap-3">
              <p className="text-[14.5px]" style={{ color: "var(--ink-2)" }}>Tickers and sectors you follow collect their stories here.</p>
              <Link href="/signin?next=/you" className="btn btn-secondary btn-sm">Sign in to follow</Link>
            </div>
          )}
        </section>

        <section className="mt-8" aria-labelledby="account-title">
          <SectionHead id="account-title" title="Account" />
          <div className="card divide-y p-0" style={{ borderColor: "var(--line)" }}>
            <div className="flex min-h-[56px] items-center px-4" style={{ borderColor: "var(--line)" }}>
              <span className="text-[15px]">Theme</span>
              <span className="ml-auto"><ThemeToggle /></span>
            </div>
            {session ? (
              <button onClick={signOut} className="flex min-h-[56px] w-full items-center px-4 text-left text-[15px] font-semibold" style={{ color: "var(--danger)", borderColor: "var(--line)" }}>
                Sign out
              </button>
            ) : (
              <Link href="/signin" className="flex min-h-[56px] items-center px-4 text-[15px] font-semibold" style={{ borderColor: "var(--line)" }}>Sign in</Link>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
