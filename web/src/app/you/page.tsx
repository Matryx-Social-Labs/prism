"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Masthead } from "@/components/Masthead";
import { PlanCard } from "@/components/PlanCard";
import { StateSelect, SubjectToggles, followedSubjects, interestsToPicks, picksToInterests, useTaxonomy, useProfessionGroups, type Picks } from "@/components/ProfileEditor";
import { SectionHead } from "@/components/SectionHead";
import { SignalRow, SubjectChip, splitFollows, tickerHref } from "@/components/accounts/signals";
import { ThemeChoice } from "@/components/accounts/ThemeChoice";
import { TickerChip } from "@/components/tabs/Markets";
import { EmptyState, SelectField, Toast } from "@/components/ui";
import type { ProfessionOption } from "@/lib/api";
import { langName, langNative } from "@/lib/languages";
import { lensMeta } from "@/lib/lenses";
import { loadProfile, saveProfile } from "@/lib/profile";
import { clearSession, useSession } from "@/lib/session";
import { getWatchlist, watchlistEvents, type WatchEvent, type WatchItem } from "@/lib/watchlist";

/**
 * You (Design System v2 · Accounts board, flow 04): your profile — state,
 * profession and the reading it picks, the subjects you follow — then what you
 * follow on the watchlist, then the account. The profile is the one onboarding
 * writes (lib/profile, this browser); Save re-sorts the record and says so.
 */
const TOAST_MS = 4000;
const LINK = "inline-flex min-h-11 items-center";

export default function YouPage() {
  const session = useSession();
  const taxonomy = useTaxonomy();
  const groups = useProfessionGroups();
  const [loaded, setLoaded] = useState(false);
  const [state, setState] = useState("");
  const [lens, setLens] = useState("reader");
  const [profession, setProfession] = useState<string | null>(null);
  const [picks, setPicks] = useState<Picks>({});
  const [languages, setLanguages] = useState<string[]>(["en"]);
  const [editing, setEditing] = useState(false);
  const [toast, setToast] = useState(false);
  const [follows, setFollows] = useState<WatchItem[]>([]);
  const [recent, setRecent] = useState<WatchEvent[]>([]);

  useEffect(() => {
    const p = loadProfile();
    if (p) {
      setLens(p.lens);
      if (p.state) setState(p.state);
      setPicks(interestsToPicks(p.interests));
      if (p.languages?.length) setLanguages(p.languages);
    }
    setLoaded(true);
  }, []);

  useEffect(() => {
    if (!session) return;
    getWatchlist(session).then(setFollows).catch(() => setFollows([]));
    watchlistEvents(session).then(setRecent).catch(() => setRecent([]));
  }, [session]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(false), TOAST_MS);
    return () => clearTimeout(t);
  }, [toast]);

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
    setEditing(false);
    setToast(true);
  };

  const signOut = () => {
    clearSession();
    window.location.href = "/feed";
  };

  const meta = lensMeta(lens);
  const subjects = followedSubjects(picks);
  const { tickers, subjects: followedSectors } = splitFollows(follows);
  const followedCount = tickers.length + followedSectors.length;
  // Only a reader's own choice is shown: the stored default (English alone) is not a pick.
  const pickedLanguages = languages.length > 1 || languages[0] !== "en";

  const profile = (
    <section className="grid content-start gap-3.5" aria-labelledby="profile-title">
      <SectionHead id="profile-title" title="Your profile" sub="Kept in this browser · sorts your record" />
      {loaded && (
        <form className="grid gap-3.5" onSubmit={(e) => { e.preventDefault(); save(); }}>
          <StateSelect value={state} onChange={setState} />
          <SelectField
            label="Profession"
            value={profession ?? ""}
            onChange={(v) => { const p = groups.flatMap((g) => g.options).find((o) => o.slug === v); if (p) pickProfession(p); }}
            placeholder="Choose your profession"
        groups={[...groups.map((g) => ({ label: g.group, options: g.options.map((o) => ({ value: o.slug, label: o.label })) }))]}
            hint={<>Reads as <span className={`p-lensdot p-l-${meta.slug} align-middle`}><i />{meta.short}</span></>}
          />
          <div role="group" aria-labelledby="you-subjects" className="grid gap-2">
            <p id="you-subjects" className="p-field__label">Subjects</p>
            {editing ? (
              <SubjectToggles taxonomy={taxonomy} picks={picks} onPicks={setPicks} />
            ) : (
              <div className="flex flex-wrap items-center gap-1.5">
                {subjects.length === 0 && <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>None yet. Follow nothing and the record is everyone&rsquo;s.</p>}
                {subjects.map(({ group, topics }) => (
                  <SubjectChip key={group.slug}>{topics ? `${group.name} · ${topics} ${topics === 1 ? "topic" : "topics"}` : group.name}</SubjectChip>
                ))}
                <button type="button" className="p-btn p-btn--text p-btn--sm" onClick={() => setEditing(true)} aria-label={subjects.length ? "Change subjects" : undefined}>
                  {subjects.length ? "Change" : "Choose subjects"}
                </button>
              </div>
            )}
          </div>
          {pickedLanguages && (
            <div className="grid gap-1.5">
              <p className="p-field__label">Languages</p>
              <p style={{ font: "var(--t-body-s)" }}>
                {languages.map((c) => (c === "en" ? langName(c) : langNative(c))).join(" · ")}
                {languages.length > 1 && <span className="p-count ml-2">IN THIS ORDER</span>}
              </p>
            </div>
          )}
          <button type="submit" className="p-btn p-btn--primary p-btn--block">Save and re-sort my record</button>
        </form>
      )}
    </section>
  );

  const following = (
    <section className="grid content-start gap-3" aria-labelledby="following-title">
      <SectionHead
        id="following-title"
        title="Following"
        sub={session && followedCount ? `${followedCount} followed` : undefined}
        right={session ? <Link href="/watchlist" className={`p-link ${LINK} text-[13.5px]`}>Watchlist →</Link> : undefined}
      />
      {session ? (
        <>
          {followedCount > 0 ? (
            <ul className="flex flex-wrap items-center gap-2">
              {tickers.map((w) => <li key={w.id}><TickerChip symbol={w.value} href={tickerHref(w.value)} /></li>)}
              {followedSectors.map((s) => <li key={s.key}><SubjectChip>{s.name}</SubjectChip></li>)}
            </ul>
          ) : (
            <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>Nothing followed yet. Follow tickers and subjects on your watchlist.</p>
          )}
          {recent.length > 0 && (
            <ol className="grid gap-2" aria-label="Recent on your signals">
              {recent.slice(0, 2).map((e) => <SignalRow key={e.id} ev={e} />)}
            </ol>
          )}
        </>
      ) : (
        <EmptyState title="Sign in to follow" action={<Link href="/signin?next=/you" className="p-btn p-btn--secondary p-btn--sm">Sign in</Link>}>
          Follow tickers and subjects, free with an account. Stories that name them collect here.
        </EmptyState>
      )}
    </section>
  );

  const account = (
    <section className="grid content-start gap-3" aria-labelledby="account-title">
      <SectionHead id="account-title" title="Account" />
      <ThemeChoice />
      {session ? (
        <>
          <div className="border-t" style={{ borderColor: "var(--line)" }}><PlanCard session={session} compact /></div>
          <p className="p-count" style={{ overflowWrap: "anywhere", whiteSpace: "normal" }}>{session.email}</p>
          <div className="flex flex-wrap items-center gap-x-4" style={{ font: "600 14.5px/1 var(--font-read)" }}>
            <Link href="/account" className={`p-link ${LINK}`}>Account and payments</Link>
            <button type="button" onClick={signOut} className={LINK} style={{ fontWeight: 500, color: "var(--ink-2)" }}>Sign out</button>
          </div>
        </>
      ) : (
        <Link href="/signin?next=/you" className="p-btn p-btn--secondary p-btn--block">Sign in</Link>
      )}
      {/* The footer is desktop-only; on the phone this is where the policies live. */}
      <div className="flex flex-wrap gap-x-3.5" style={{ font: "400 13px/1 var(--font-read)", color: "var(--ink-3)" }}>
        <Link href="/privacy" className={`${LINK} underline underline-offset-[3px]`}>Privacy</Link>
        <Link href="/terms" className={`${LINK} underline underline-offset-[3px]`}>Terms</Link>
        <Link href="/refunds" className={`${LINK} underline underline-offset-[3px]`}>Refunds</Link>
      </div>
    </section>
  );

  return (
    <div className="mx-auto max-w-[var(--reading)] px-[var(--gutter)] pb-[calc(var(--tabbar)+24px)] lg:max-w-[1040px] lg:pb-12">
      <Masthead dateline="You" />
      <div className="grid gap-7 pt-4 lg:pt-9">
        <div className="grid gap-1">
          <h1 className="[font:var(--t-display-m)] lg:[font:var(--t-display-l)]" style={{ letterSpacing: "var(--track-display)" }}>You</h1>
          <p className="p-count" style={{ overflowWrap: "anywhere", whiteSpace: "normal" }}>{session ? session.email : "Not signed in"}</p>
        </div>
        <div className="grid gap-7 lg:grid-cols-2 lg:gap-12">
          {profile}
          <div className="grid content-start gap-7 lg:gap-9">
            {following}
            {account}
          </div>
        </div>
      </div>
      {/* Always mounted, so the live region exists before the words arrive. */}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-[calc(var(--tabbar)+16px+env(safe-area-inset-bottom))] z-50 flex justify-center px-[var(--gutter)] lg:bottom-6">
        {toast && <Toast>Saved · your record is re-sorted</Toast>}
      </div>
    </div>
  );
}
