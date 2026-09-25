"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Masthead } from "@/components/Masthead";
import { PlanCard } from "@/components/PlanCard";
import { StateSelect, groupOn, interestsToPicks, picksToInterests, toggleGroup, toggleSub, useTaxonomy, type Picks } from "@/components/ProfileEditor";
import { useProfessionGroups } from "@/components/ReservationForm";
import { SectionHead } from "@/components/SectionHead";
import { TickerChip } from "@/components/tabs/Markets";
import type { ProfessionOption, TaxonomySector } from "@/lib/api";
import { lensMeta } from "@/lib/lenses";
import { loadProfile, saveProfile } from "@/lib/profile";
import { SECTOR_GROUPS, sectorGroup, type SectorGroup } from "@/lib/sectors";
import { clearSession, useSession } from "@/lib/session";
import { getWatchlist, watchlistEvents, type WatchEvent, type WatchItem } from "@/lib/watchlist";
import { Ago } from "@/components/Ago";

/**
 * You (Design System v2 · reader-phone PhoneYou): "Your record" — where you
 * are, what you do, the subjects you follow — then what you follow on the
 * watchlist and the account. Saving re-sorts For you, so Save returns to the
 * chart. The profile is the same one onboarding writes (lib/profile).
 */
const plural = (n: number, one: string) => `${n} ${n === 1 ? one : `${one}s`}`;

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
  const professions = groups.flatMap((g) => g.options);
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

  const meta = lensMeta(lens);
  const tickers = follows.filter((w) => w.kind === "ticker");
  const sectors = follows.filter((w) => w.kind !== "ticker");
  const followingSub = follows.length ? [tickers.length ? plural(tickers.length, "ticker") : null, sectors.length ? plural(sectors.length, "sector") : null].filter(Boolean).join(" · ") : undefined;

  return (
    <div className="mx-auto max-w-[var(--reading)] px-[var(--gutter)] pb-[calc(var(--tabbar)+24px)] lg:max-w-[760px] lg:pb-12">
      <Masthead dateline="You" />
      <div className="grid gap-5 pt-4 lg:pt-6">
        <SectionHead
          id="you-title"
          as="h1"
          title="Your record"
          sub={session ? `Signed in as ${session.email}` : undefined}
          hint={session ? undefined : "Your profile lives in this browser; no account needed."}
        />

        {loaded && (
          <form className="grid gap-3.5" onSubmit={(e) => { e.preventDefault(); save(); }}>
            <div className="p-field">
              <label className="p-field__label" htmlFor="you-state">State</label>
              <StateSelect id="you-state" value={state} onChange={setState} />
            </div>
            <div className="p-field">
              <label className="p-field__label" htmlFor="you-profession">What you do</label>
              <select
                id="you-profession"
                className="p-input"
                value={profession ?? ""}
                onChange={(e) => { const p = professions.find((o) => o.slug === e.target.value); if (p) pickProfession(p); }}
                style={{ color: profession ? "var(--ink)" : "var(--ink-3)" }}
              >
                <option value="" disabled>Choose your profession…</option>
                {groups.map((g) => (
                  <optgroup key={g.group} label={g.group}>
                    {g.options.map((o) => <option key={o.slug} value={o.slug} style={{ color: "var(--ink)" }}>{o.label}</option>)}
                  </optgroup>
                ))}
              </select>
              <p className="p-field__hint">Reads as {meta.name}: {meta.plain ?? meta.tagline}. It pre-sets your subjects when you follow none.</p>
            </div>
            <div role="group" aria-labelledby="you-subjects" className="grid gap-1.5 pt-1.5">
              <p id="you-subjects" className="p-field__label">What you follow</p>
              <p className="p-field__hint">Follow nothing and the chart is everyone&rsquo;s. Follow a subject and For you appears; narrow it to the beats you actually read.</p>
              <div className="mt-1.5 border-b" style={{ borderColor: "var(--line)" }}>
                {SECTOR_GROUPS.map((g) => <SubjectToggle key={g.slug} group={g} taxonomy={taxonomy} picks={picks} onPicks={setPicks} />)}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 pt-1.5">
              <button type="submit" className="p-btn p-btn--primary p-btn--block sm:w-auto">Save and re-sort my record</button>
              <Link href="/feed" className="p-btn p-btn--ghost">Cancel</Link>
            </div>
          </form>
        )}

        <section aria-labelledby="following-title">
          <SectionHead
            id="following-title"
            title="Following"
            sub={session ? followingSub : undefined}
            right={session ? <Link href="/watchlist" className="p-btn p-btn--secondary p-btn--sm">Watchlist</Link> : undefined}
          />
          {session ? (
            <div className="grid gap-3">
              {follows.length > 0 ? (
                <ul className="flex flex-wrap items-center gap-2">
                  {tickers.map((w) => <li key={`t:${w.value}`}><TickerChip symbol={w.value} href={`/watchlist?ticker=${encodeURIComponent(w.value)}`} /></li>)}
                  {sectors.map((w) => <li key={`s:${w.value}`}><span className="p-chip">{sectorGroup(w.value)?.name ?? w.value}</span></li>)}
                </ul>
              ) : (
                <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>Nothing followed yet. Follow tickers and sectors from any story.</p>
              )}
              {recent.length > 0 && (
                <ol className="border-b" style={{ borderColor: "var(--line)" }} aria-label="Recent on your signals">
                  {recent.slice(0, 3).map((e) => (
                    <li key={e.id} className="border-t" style={{ borderColor: "var(--line)" }}>
                      <Link href={`/story/${e.id}`} className="grid gap-1 py-3">
                        <span style={{ font: "var(--t-title-s)", color: "var(--ink)" }}>{e.title}</span>
                        <Ago iso={e.last_updated_at} className="p-count" />
                      </Link>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>Tickers and sectors you follow collect their stories here.</p>
              <Link href="/signin?next=/you" className="p-btn p-btn--secondary p-btn--sm">Sign in to follow</Link>
            </div>
          )}
        </section>

        <section aria-labelledby="account-title">
          <SectionHead id="account-title" title="Account" />
          {session && <PlanCard session={session} compact />}
          {/* The footer is desktop-only; on the phone this is where the policies live. */}
          <div className="flex flex-wrap items-center gap-x-4" style={{ font: "500 14px/1 var(--font-read)" }}>
            <Link href="/privacy" className="inline-flex min-h-11 items-center">Privacy</Link>
            <Link href="/terms" className="inline-flex min-h-11 items-center">Terms</Link>
            <Link href="/refunds" className="inline-flex min-h-11 items-center">Refunds</Link>
            <span className="flex-1" />
            {session ? (
              <button type="button" onClick={signOut} className="inline-flex min-h-11 items-center" style={{ color: "var(--ink-2)" }}>Sign out</button>
            ) : (
              <Link href="/signin" className="p-link inline-flex min-h-11 items-center">Sign in</Link>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

/**
 * Design System v2 · ToggleRow: one subject, its beats named beneath, a switch;
 * following it opens its beats as chips. A subject toggles every sector it
 * groups, so picks stay in the pipeline's ten sectors.
 */
function SubjectToggle({ group, taxonomy, picks, onPicks }: { group: SectorGroup; taxonomy: TaxonomySector[]; picks: Picks; onPicks: (p: Picks) => void }) {
  const on = groupOn(picks, group.sectors);
  const subs = group.sectors.flatMap((s) => (taxonomy.find((t) => t.slug === s)?.subsectors ?? []).map((sub) => ({ sector: s, ...sub })));
  return (
    <div className="border-t" style={{ borderColor: "var(--line)" }}>
      <button type="button" aria-pressed={on} onClick={() => onPicks(toggleGroup(picks, group.sectors))} className="flex min-h-14 w-full items-center gap-3 py-2 text-left">
        <span className="grid min-w-0 flex-1 gap-0.5">
          <span style={{ font: "600 15px/1.3 var(--font-read)", color: "var(--ink)" }}>{group.name}</span>
          {subs.length > 0 && <span style={{ font: "400 13.5px/1.4 var(--font-read)", color: "var(--ink-3)" }}>{subs.map((s) => s.name).join(" · ")}</span>}
        </span>
        <span className="p-switch" aria-checked={on} aria-hidden="true" />
      </button>
      {on && subs.length > 0 && (
        <div className="flex flex-wrap gap-2 pb-3.5">
          {subs.map((sub) => {
            const cur = picks[sub.sector];
            const sel = Array.isArray(cur) && cur.includes(sub.slug);
            return (
              <button key={`${sub.sector}:${sub.slug}`} type="button" onClick={() => onPicks(toggleSub(picks, sub.sector, sub.slug))} aria-pressed={sel} className="p-chip">
                {sub.name}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
